import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/extend-expect';
import CustomProvisions from '../components/CustomProvisions';
import { useCustomProvisions } from '../hooks/useCustomProvisions';

// Mock du hook personnalisé
jest.mock('../hooks/useCustomProvisions', () => ({
  useCustomProvisions: jest.fn()
}));

describe('CustomProvisions Component', () => {
  const mockProvisions = [
    {
      id: '1',
      name: 'Investissement',
      percentage: 10,
      calculationBase: 'revenu_net',
      membersDistribution: { 'user1': 0.5, 'user2': 0.5 }
    },
    {
      id: '2', 
      name: 'Épargne Vacances', 
      percentage: 15,
      calculationBase: 'revenu_total',
      membersDistribution: { 'user1': 1.0 }
    }
  ];

  beforeEach(() => {
    useCustomProvisions.mockReturnValue({
      provisions: mockProvisions,
      addProvision: jest.fn(),
      updateProvision: jest.fn(),
      deleteProvision: jest.fn()
    });
  });

  test('Rend la liste des provisions', () => {
    render(<CustomProvisions />);
    
    expect(screen.getByText('Investissement')).toBeInTheDocument();
    expect(screen.getByText('Épargne Vacances')).toBeInTheDocument();
  });

  test('Ouvre le formulaire de création', async () => {
    render(<CustomProvisions />);
    
    const addButton = screen.getByText('Ajouter une provision');
    fireEvent.click(addButton);
    
    await waitFor(() => {
      expect(screen.getByText('Nouvelle Provision')).toBeInTheDocument();
    });
  });

  test('Calcul en temps réel du montant', async () => {
    render(<CustomProvisions />);
    
    const revenuInput = screen.getByLabelText('Revenu Net');
    fireEvent.change(revenuInput, { target: { value: '5000' } });
    
    await waitFor(() => {
      expect(screen.getByText('Montant Investissement: 500€')).toBeInTheDocument();
      expect(screen.getByText('Montant Épargne Vacances: 750€')).toBeInTheDocument();
    });
  });

  test('Modification de provision', async () => {
    render(<CustomProvisions />);
    
    const editButtons = screen.getAllByText('Modifier');
    fireEvent.click(editButtons[0]);
    
    await waitFor(() => {
      expect(screen.getByText('Modifier Provision')).toBeInTheDocument();
    });
    
    const nameInput = screen.getByLabelText('Nom');
    fireEvent.change(nameInput, { target: { value: 'Nouvel Investissement' } });
    
    const saveButton = screen.getByText('Enregistrer');
    fireEvent.click(saveButton);
    
    await waitFor(() => {
      expect(useCustomProvisions().updateProvision).toHaveBeenCalled();
    });
  });

  test('Suppression de provision', async () => {
    render(<CustomProvisions />);
    
    const deleteButtons = screen.getAllByText('Supprimer');
    fireEvent.click(deleteButtons[0]);
    
    await waitFor(() => {
      expect(useCustomProvisions().deleteProvision).toHaveBeenCalled();
    });
  });

  // Tests d'accessibilité
  test('Composant respecte les normes WCAG', async () => {
    const { container } = render(<CustomProvisions />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  // Tests responsive
  test('Affichage responsive', () => {
    const { container } = render(<CustomProvisions />);
    
    // Simuler différentes tailles d'écran
    const sizes = [
      { width: 320, height: 568 },   // Mobile
      { width: 768, height: 1024 },  // Tablette
      { width: 1024, height: 768 }   // Desktop
    ];
    
    sizes.forEach(size => {
      window.innerWidth = size.width;
      window.innerHeight = size.height;
      window.dispatchEvent(new Event('resize'));
      
      // Vérifier que le layout s'adapte correctement
      const provisionsList = screen.getByTestId('provisions-list');
      expect(provisionsList).toHaveStyle(`
        display: ${size.width < 768 ? 'block' : 'flex'}
      `);
    });
  });
});