/**
 * Tests for ReasoningCompanion component
 */

import { render, screen, waitFor } from '@testing-library/react';
import { ReasoningCompanion } from '../ReasoningCompanion';

// Mock the useReasoningCompanion hook
jest.mock('@/hooks/useReasoningCompanion', () => ({
  useReasoningCompanion: jest.fn()
}));

import { useReasoningCompanion } from '@/hooks/useReasoningCompanion';

const mockUseReasoningCompanion = useReasoningCompanion as jest.MockedFunction<typeof useReasoningCompanion>;

describe('ReasoningCompanion', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders nothing when threadId is null', () => {
    mockUseReasoningCompanion.mockReturnValue({
      reflection: null,
      backgroundActivity: null,
      isActive: false,
      error: null,
      clearError: jest.fn()
    });

    const { container } = render(<ReasoningCompanion threadId={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows analyzing state when active but no data', () => {
    mockUseReasoningCompanion.mockReturnValue({
      reflection: null,
      backgroundActivity: null,
      isActive: true,
      error: null,
      clearError: jest.fn()
    });

    render(<ReasoningCompanion threadId="test-thread-id" />);
    expect(screen.getByText(/analyzing/i)).toBeInTheDocument();
  });

  it('displays reflection text when available', () => {
    mockUseReasoningCompanion.mockReturnValue({
      reflection: {
        id: 'reflection-1',
        text: 'This is a test reflection.\n\nIt has multiple paragraphs.',
        trigger_type: 'user_message',
        patterns: {
          ungrounded_assumptions: [],
          contradictions: [],
          strong_claims: [],
          recurring_themes: [],
          missing_considerations: []
        },
        created_at: new Date().toISOString()
      },
      backgroundActivity: null,
      isActive: true,
      error: null,
      clearError: jest.fn()
    });

    render(<ReasoningCompanion threadId="test-thread-id" />);
    expect(screen.getByText(/This is a test reflection/)).toBeInTheDocument();
  });

  it('displays background activity when available', () => {
    mockUseReasoningCompanion.mockReturnValue({
      reflection: null,
      backgroundActivity: {
        signals_extracted: {
          count: 3,
          by_type: {},
          items: [
            { text: 'Test signal 1', type: 'Assumption' },
            { text: 'Test signal 2', type: 'Claim' }
          ]
        },
        evidence_linked: {
          count: 2,
          sources: ['doc1.pdf', 'doc2.pdf']
        },
        connections_built: {
          count: 1
        },
        confidence_updates: []
      },
      isActive: true,
      error: null,
      clearError: jest.fn()
    });

    render(<ReasoningCompanion threadId="test-thread-id" />);
    expect(screen.getByText(/Extracted 3 signal/)).toBeInTheDocument();
    expect(screen.getByText(/Linked 2 piece/)).toBeInTheDocument();
  });

  it('displays confidence updates', () => {
    mockUseReasoningCompanion.mockReturnValue({
      reflection: null,
      backgroundActivity: {
        signals_extracted: { count: 0, by_type: {}, items: [] },
        evidence_linked: { count: 0, sources: [] },
        connections_built: { count: 0 },
        confidence_updates: [
          {
            inquiry_id: 'inq-1',
            title: 'Should we migrate?',
            old: 0.75,
            new: 0.45
          }
        ]
      },
      isActive: true,
      error: null,
      clearError: jest.fn()
    });

    render(<ReasoningCompanion threadId="test-thread-id" />);
    expect(screen.getByText(/Should we migrate/)).toBeInTheDocument();
    expect(screen.getByText(/75%/)).toBeInTheDocument();
    expect(screen.getByText(/45%/)).toBeInTheDocument();
  });

  it('shows error message when connection fails', () => {
    mockUseReasoningCompanion.mockReturnValue({
      reflection: null,
      backgroundActivity: null,
      isActive: false,
      error: 'Connection lost',
      clearError: jest.fn()
    });

    render(<ReasoningCompanion threadId="test-thread-id" />);
    expect(screen.getByText(/Connection lost/)).toBeInTheDocument();
  });

  it('shows active indicator when connected', () => {
    mockUseReasoningCompanion.mockReturnValue({
      reflection: null,
      backgroundActivity: null,
      isActive: true,
      error: null,
      clearError: jest.fn()
    });

    const { container } = render(<ReasoningCompanion threadId="test-thread-id" />);
    
    // Check for active pulse indicator
    const indicator = container.querySelector('.animate-pulse');
    expect(indicator).toBeInTheDocument();
    expect(indicator).toHaveClass('bg-primary-500');
  });
});
