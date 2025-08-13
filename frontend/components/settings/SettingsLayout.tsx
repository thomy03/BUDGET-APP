'use client';

import { useState } from 'react';
import { Card, Button } from '../ui';

interface SettingsSection {
  id: string;
  title: string;
  icon: string;
  description: string;
  component: React.ReactNode;
}

interface SettingsLayoutProps {
  sections: SettingsSection[];
  defaultTab?: string;
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
  children?: React.ReactNode;
}

export function SettingsLayout({ sections, defaultTab, activeTab, onTabChange, children }: SettingsLayoutProps) {
  const [internalActiveSection, setInternalActiveSection] = useState(defaultTab || 'budget');
  
  // Utiliser activeTab externe si fourni, sinon utiliser l'état interne
  const activeSection = activeTab !== undefined ? activeTab : internalActiveSection;
  
  const handleSectionChange = (sectionId: string) => {
    if (onTabChange) {
      onTabChange(sectionId);
    } else {
      setInternalActiveSection(sectionId);
    }
  };

  const currentSection = sections.find(s => s.id === activeSection) || sections[0];

  return (
    <div className="max-w-7xl mx-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Paramètres
          </h1>
          <p className="text-gray-600 mt-1">
            Configurez votre budget et personnalisez votre expérience
          </p>
        </div>
        <div className="flex items-center gap-3">
          {children}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Navigation */}
        <div className="lg:col-span-1">
          <nav className="space-y-2">
            {sections.map((section, index) => (
              <button
                key={section.id}
                onClick={() => handleSectionChange(section.id)}
                className={`w-full text-left px-4 py-3 rounded-lg transition-all duration-200 ${
                  activeSection === section.id
                    ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-200'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="flex items-center">
                  <span className="text-xl mr-3">{section.icon}</span>
                  <div className="min-w-0 flex-1">
                    <div className="font-medium truncate">{section.title}</div>
                    <div className="text-xs text-gray-500 truncate mt-1">{section.description}</div>
                  </div>
                </div>
              </button>
            ))}
          </nav>
        </div>

        {/* Main Content Area */}
        <div className="lg:col-span-3">
          {currentSection && (
            <div className="space-y-6">
              {/* Section Header */}
              <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                <div className="flex items-center mb-2">
                  <span className="text-2xl mr-3">{currentSection.icon}</span>
                  <h2 className="text-2xl font-bold text-gray-900">{currentSection.title}</h2>
                </div>
                <p className="text-gray-600">{currentSection.description}</p>
              </div>

              {/* Section Content */}
              <div className="min-h-[400px]">
                {currentSection.component}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}