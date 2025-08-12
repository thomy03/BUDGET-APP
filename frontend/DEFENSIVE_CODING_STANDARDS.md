# 🛡️ DEFENSIVE CODING STANDARDS

## CRITICAL RUNTIME ERROR PREVENTION

This document establishes **mandatory coding standards** to prevent runtime errors caused by undefined/null property access.

## 🚨 ZERO TOLERANCE POLICY

**Runtime errors due to undefined property access are UNACCEPTABLE in production.**

All components must follow these defensive programming patterns.

## 📋 MANDATORY CHECKLIST

Before any component goes to production, verify:

- [ ] All array operations use safe utilities (`safeArray`, `safeMap`, `safeSlice`)
- [ ] All object property access is protected with optional chaining (`?.`)
- [ ] All enum/config lookups have fallbacks
- [ ] Critical components are wrapped in Error Boundaries
- [ ] Props are validated using `validateRequiredProps`
- [ ] Type guards are used for union types

## 🔧 REQUIRED PATTERNS

### 1. ARRAY OPERATIONS - ALWAYS SAFE

```typescript
// ❌ UNSAFE - Can cause runtime errors
items.map(item => ...)
data.slice(0, 5)
users.filter(u => u.active)

// ✅ SAFE - Always works
safeMap(items, item => ...)
safeSlice(data, 0, 5)
safeFilter(users, u => u.active)
```

### 2. OBJECT PROPERTY ACCESS - OPTIONAL CHAINING

```typescript
// ❌ UNSAFE
const config = typeConfig[type];
const label = config.label; // ❌ Crashes if config is undefined

// ✅ SAFE
const config = typeConfig[type];
if (!config) return null; // Early return
const label = config.label; // ✅ Safe

// OR
const label = typeConfig[type]?.label; // ✅ Safe with optional chaining
```

### 3. PROP VALIDATION - REQUIRED

```typescript
// ✅ REQUIRED for all components with critical props
export function MyComponent({ criticalProp, optionalProp }: Props) {
  if (!validateRequiredProps({ criticalProp }, ['criticalProp'], 'MyComponent')) {
    return null;
  }
  
  // Rest of component logic...
}
```

### 4. TYPE GUARDS - UNION TYPES

```typescript
// ❌ UNSAFE
const config = typeConfig[type]; // type could be invalid

// ✅ SAFE
if (!isValidExpenseType(type)) {
  console.error(`Invalid type: ${type}`);
  return null;
}
const config = typeConfig[type]; // Now safe
```

### 5. ERROR BOUNDARIES - CRITICAL COMPONENTS

```typescript
// ✅ REQUIRED for components that handle external data
<ErrorBoundary componentName="TransactionRow">
  <TransactionRow {...props} />
</ErrorBoundary>

// ✅ For inline components
<ErrorBoundary 
  componentName="ExpenseTypeBadge" 
  fallback={<span className="text-red-500">❌</span>}
>
  <ExpenseTypeBadge type={tag.expense_type} />
</ErrorBoundary>
```

## 🚫 FORBIDDEN PATTERNS

### NEVER DO THIS:

```typescript
// ❌ Direct array methods without null checks
data.map(...)
items.filter(...)
list.slice(...)

// ❌ Direct property access on potentially undefined objects
config[type].label
user.profile.avatar

// ❌ Assuming props are always defined
function Component({ items }: { items: Item[] | undefined }) {
  return items.map(...) // ❌ CRASHES if items is undefined
}

// ❌ No error boundaries around external data components
<ExpenseTypeBadge type={unknownType} />
```

## 📚 UTILITY FUNCTIONS

All components must import and use:

```typescript
import { 
  safeArray, 
  safeMap, 
  safeFilter, 
  safeSlice,
  validateRequiredProps,
  isValidExpenseType,
  getSafeEnumValue 
} from '../../types/defensive-programming';

import { ErrorBoundary } from '../ui';
```

## 🧪 TESTING REQUIREMENTS

All components must be tested with:

1. **Undefined props**: `undefined`, `null`
2. **Empty arrays**: `[]`
3. **Invalid enum values**: Invalid type strings
4. **Malformed data**: Unexpected object shapes

## 🚀 IMPLEMENTATION EXAMPLES

### Safe Component Template:

```typescript
'use client';

import { validateRequiredProps, safeMap } from '../../types/defensive-programming';
import { ErrorBoundary } from '../ui';

interface MyComponentProps {
  items: Item[] | undefined;
  config: Config | null;
  type: 'fixed' | 'variable' | null;
}

export function MyComponent({ items, config, type }: MyComponentProps) {
  // 1. Validate critical props
  if (!validateRequiredProps({ type }, ['type'], 'MyComponent') || !type) {
    return null;
  }
  
  // 2. Safe array operations
  const displayItems = safeMap(items, item => (
    <ErrorBoundary key={item.id} componentName="ItemComponent">
      <ItemComponent item={item} />
    </ErrorBoundary>
  ));
  
  // 3. Safe object access
  const title = config?.title || 'Default Title';
  
  return (
    <div>
      <h2>{title}</h2>
      <div>{displayItems}</div>
    </div>
  );
}
```

## 🔍 CODE REVIEW REQUIREMENTS

All pull requests must be reviewed for:

1. **Safe array operations** - No direct `.map()`, `.filter()`, `.slice()`
2. **Proper null checks** - All object access protected
3. **Error boundaries** - Critical components wrapped
4. **Prop validation** - Required props validated
5. **Type safety** - No unsafe type assertions

## ⚡ PERFORMANCE NOTES

These patterns have **minimal performance impact** and provide:

- ✅ **Zero runtime errors**
- ✅ **Better debugging**
- ✅ **Improved user experience**
- ✅ **Easier maintenance**

## 🚀 ENFORCEMENT

**These standards are MANDATORY**. Code that doesn't follow these patterns will be:

1. **Rejected in code review**
2. **Flagged by automated checks**
3. **Require immediate refactoring**

Remember: **Better safe than sorry. Zero tolerance for preventable runtime errors.**