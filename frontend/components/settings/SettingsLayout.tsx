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
    <div className="max-w-7xl mx-auto p-3 xs:p-4 md:p-6">
      {/* Header */}
      <div className="flex flex-col xs:flex-row xs:items-center xs:justify-between gap-3 xs:gap-4 mb-4 xs:mb-6 md:mb-8">
        <div className="min-w-0 flex-1">
          <h1 className="text-xl xs:text-2xl md:text-3xl font-bold text-gray-900 truncate">
            Paramètres
          </h1>
          <p className="text-xs xs:text-sm md:text-base text-gray-600 mt-1 line-clamp-2">
            Configurez votre budget et personnalisez votre expérience
          </p>
        </div>
        <div className="flex items-center gap-2 xs:gap-3 flex-shrink-0">
          {children}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 md:gap-6">
        {/* Mobile: Horizontal Scrolling Tabs */}
        <div className="lg:hidden">
          <nav className="flex overflow-x-auto gap-2 pb-2 -mx-3 xs:-mx-4 px-3 xs:px-4 scrollbar-hide">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => handleSectionChange(section.id)}
                className={`flex-shrink-0 min-h-[44px] px-3 xs:px-4 py-2 rounded-lg transition-all duration-200 ${
                  activeSection === section.id
                    ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-200'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 border border-gray-200'
                }`}
              >
                <div className="flex items-center gap-2 whitespace-nowrap">
                  <span className="text-base xs:text-lg">{section.icon}</span>
                  <span className="text-xs xs:text-sm font-medium">{section.title}</span>
                </div>
              </button>
            ))}
          </nav>
        </div>

        {/* Desktop: Sidebar Navigation */}
        <div className="hidden lg:block lg:col-span-1">
          <nav className="space-y-2">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => handleSectionChange(section.id)}
                className={`w-full text-left px-4 py-3 rounded-lg transition-all duration-200 min-h-[44px] ${
                  activeSection === section.id
                    ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-200'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="flex items-center">
                  <span className="text-xl mr-3 flex-shrink-0">{section.icon}</span>
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
            <div className="space-y-4 md:space-y-6">
              {/* Section Header - Hidden on mobile (shown in tabs), visible on desktop */}
              <div className="hidden lg:block bg-white border border-gray-200 rounded-lg p-4 md:p-6 shadow-sm">
                <div className="flex items-center mb-2">
                  <span className="text-xl md:text-2xl mr-3">{currentSection.icon}</span>
                  <h2 className="text-xl md:text-2xl font-bold text-gray-900">{currentSection.title}</h2>
                </div>
                <p className="text-sm md:text-base text-gray-600">{currentSection.description}</p>
              </div>

              {/* Mobile Section Title */}
              <div className="lg:hidden bg-white border border-gray-200 rounded-lg p-3 xs:p-4 shadow-sm">
                <div className="flex items-center gap-2">
                  <span className="text-lg xs:text-xl">{currentSection.icon}</span>
                  <h2 className="text-base xs:text-lg font-bold text-gray-900">{currentSection.title}</h2>
                </div>
                <p className="text-xs xs:text-sm text-gray-600 mt-1 line-clamp-2">{currentSection.description}</p>
              </div>

              {/* Section Content */}
              <div className="min-h-[300px] xs:min-h-[400px]">
                {currentSection.component}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}