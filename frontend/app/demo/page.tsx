'use client';

import { ClassificationDemo } from '../../components/demo/ClassificationDemo';

/**
 * Page de démonstration pour tester l'interface de classification intelligente
 * URL: /demo
 */
export default function DemoPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <ClassificationDemo />
    </div>
  );
}