# Tag Suggestion API Documentation

## Overview

The Tag Suggestion API provides intelligent, contextual tag suggestions for financial transactions using machine learning and web research. This system replaces traditional FIXED/VARIABLE classification with semantic, contextual tags that provide better insights into spending patterns.

## Features

- **Intelligent Merchant Recognition**: Automatically identifies merchants and suggests relevant tags
- **Web Research Integration**: Uses real-time web research for unknown merchants
- **High-Performance Batch Processing**: Efficient processing of multiple transactions
- **Learning System**: Improves suggestions based on user feedback
- **Fallback Mechanisms**: Robust handling of edge cases and failures
- **Confidence Scoring**: Provides transparency about suggestion quality

## API Endpoints

### 1. Single Tag Suggestion

**POST** `/api/classification/tags/suggest`

Suggest a contextual tag for a single transaction.

#### Request Body
```json
{
  "transaction_label": "NETFLIX SARL 12.99",
  "transaction_amount": 12.99,
  "use_web_research": true
}
```

#### Response
```json
{
  "suggested_tag": "streaming",
  "confidence": 0.95,
  "explanation": "Marchand reconnu: Netflix → streaming",
  "alternative_tags": ["divertissement", "abonnement"],
  "merchant_category": "streaming",
  "research_source": "merchant_pattern",
  "web_research_used": false,
  "merchant_info": null,
  "processing_time_ms": 15,
  "fallback_used": false
}
```

#### Use Cases
- Real-time tag suggestions during manual transaction entry
- Individual transaction classification
- Interactive suggestion UI components

---

### 2. Batch Tag Suggestions

**POST** `/api/classification/tags/suggest-batch`

Process multiple transactions efficiently for tag suggestions.

#### Request Body
```json
{
  "transactions": [
    {"id": 1, "label": "NETFLIX SARL 12.99", "amount": 12.99},
    {"id": 2, "label": "CARREFOUR VILLENEUVE 45.67", "amount": 45.67},
    {"id": 3, "label": "TOTAL ACCESS PARIS 62.30", "amount": 62.30}
  ],
  "use_web_research": false
}
```

#### Response
```json
{
  "results": {
    "1": {
      "suggested_tag": "streaming",
      "confidence": 0.95,
      "explanation": "Marchand reconnu: Netflix → streaming",
      "alternative_tags": ["divertissement", "abonnement"],
      "merchant_category": "streaming",
      "research_source": "merchant_pattern",
      "web_research_used": false,
      "processing_time_ms": 0,
      "fallback_used": false
    },
    "2": {
      "suggested_tag": "courses",
      "confidence": 0.98,
      "explanation": "Marchand reconnu: Carrefour → courses",
      "alternative_tags": ["alimentation", "supermarche"],
      "merchant_category": "supermarket",
      "research_source": "merchant_pattern",
      "web_research_used": false,
      "processing_time_ms": 0,
      "fallback_used": false
    }
  },
  "summary": {
    "method": "pattern_matching",
    "high_confidence_threshold": 0.8,
    "avg_processing_time_per_tx": 8.33
  },
  "total_processed": 3,
  "processing_time_ms": 25,
  "web_research_count": 0,
  "high_confidence_count": 2,
  "average_confidence": 0.91
}
```

#### Performance
- **Without web research**: ~50-100 transactions/second
- **With web research**: ~10-20 transactions/second (parallel requests)

#### Use Cases
- Bulk import classification
- Monthly re-classification
- Initial setup for existing transaction data

---

### 3. Learning from Feedback

**POST** `/api/classification/tags/learn`

Improve suggestions by learning from user corrections.

#### Request Body
```json
{
  "transaction_label": "NETFLIX SARL 12.99",
  "suggested_tag": "streaming",
  "actual_tag": "divertissement",
  "confidence": 0.95,
  "feedback_reason": "User prefers broader category"
}
```

#### Response
```json
{
  "status": "feedback_recorded",
  "message": "Learning feedback processed successfully",
  "transaction_label": "NETFLIX SARL 12.99",
  "correction": "streaming → divertissement",
  "confidence_was": 0.95
}
```

#### Learning Signals
- High-confidence wrong suggestions (critical for improvement)
- User-preferred tags for specific merchants
- Pattern corrections for better future suggestions

---

### 4. System Statistics

**GET** `/api/classification/tags/stats`

Get comprehensive statistics about the tag suggestion system.

#### Response
```json
{
  "total_patterns": 44,
  "total_categories": 12,
  "web_research_enabled": true,
  "learning_enabled": true,
  "performance_metrics": {
    "total_rules": 68,
    "text_patterns": 12,
    "fallback_strategies": 3,
    "confidence_threshold_recommended": 0.7
  },
  "service_version": "1.0.0"
}
```

## Error Handling

All endpoints implement comprehensive error handling:

### Common Error Responses

#### 400 Bad Request
```json
{
  "detail": "Validation error: transaction_label is required"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Tag suggestion error: Web research service unavailable"
}
```

### Fallback Mechanisms

1. **Web Research Failure**: Falls back to pattern matching
2. **Unknown Merchant**: Uses amount-based heuristics
3. **Service Unavailable**: Returns generic categorization
4. **Invalid Input**: Provides clear validation errors

## Performance Characteristics

### Response Times
- **Known merchants**: <50ms (pattern matching)
- **Unknown merchants (no web research)**: <100ms
- **Unknown merchants (with web research)**: 500-2000ms
- **Batch processing (50 transactions)**: 1-3 seconds

### Confidence Thresholds
- **High confidence**: >0.8 (recommended for auto-application)
- **Medium confidence**: 0.5-0.8 (suggest with alternatives)
- **Low confidence**: <0.5 (manual review recommended)

### Cache Strategy
- Merchant patterns cached in memory
- Web research results cached for 15 minutes
- Learning patterns updated in real-time

## Integration Examples

### Frontend Integration
```typescript
// Single suggestion
const tagSuggestion = await fetch('/api/classification/tags/suggest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    transaction_label: transaction.label,
    transaction_amount: transaction.amount,
    use_web_research: true
  })
});

// Batch processing
const batchResults = await fetch('/api/classification/tags/suggest-batch', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    transactions: untaggedTransactions,
    use_web_research: false // Faster for bulk operations
  })
});
```

### Workflow Integration
1. **Import Phase**: Use batch endpoint without web research for speed
2. **User Review**: Show suggestions with confidence scores
3. **High Confidence**: Auto-apply tags with confidence >0.8
4. **Manual Review**: Present alternatives for medium confidence
5. **Learning**: Send feedback for incorrect suggestions

## Security Considerations

- All endpoints require user authentication
- Input validation prevents injection attacks
- Rate limiting prevents abuse of web research
- User data isolation in multi-tenant environment

## Monitoring and Metrics

Key metrics to monitor:
- Average confidence scores
- Web research success rate
- Processing times
- User acceptance rate
- Learning feedback volume

## Migration from FIXED/VARIABLE

The new tag suggestion system is designed to coexist with the existing FIXED/VARIABLE classification:

1. **Dual Mode**: Endpoints can return both tag suggestions and expense types
2. **Gradual Migration**: Teams can migrate incrementally
3. **Backward Compatibility**: Existing endpoints remain functional
4. **Enhanced Value**: Tags provide more granular insights than FIXED/VARIABLE

## Best Practices

1. **Use web research sparingly**: Enable only for critical unknown merchants
2. **Implement confidence thresholds**: Auto-apply only high-confidence suggestions
3. **Provide user feedback loops**: Enable learning from corrections
4. **Monitor performance**: Track processing times and accuracy
5. **Cache aggressively**: Reduce redundant processing
6. **Fallback gracefully**: Handle service failures transparently

## Support and Troubleshooting

### Common Issues
1. **Slow responses**: Disable web research for batch operations
2. **Low accuracy**: Check confidence thresholds and learning data
3. **Web research failures**: Verify network connectivity and service health
4. **Memory usage**: Monitor pattern cache size and cleanup

### Debugging
- Enable debug logging for detailed processing information
- Use the stats endpoint to monitor system health
- Check confidence scores to identify problem areas
- Review learning feedback for accuracy improvements