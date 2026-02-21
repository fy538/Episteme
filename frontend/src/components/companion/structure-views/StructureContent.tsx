/**
 * StructureContent — Dispatches to the correct view based on structure type.
 */

'use client';

import { memo } from 'react';
import type { StructureType } from '@/lib/types/companion';
import { AssumptionSurfaceView } from './AssumptionSurfaceView';
import { AngleMapView } from './AngleMapView';
import { DecisionTreeView } from './DecisionTreeView';
import { ChecklistView } from './ChecklistView';
import { ComparisonView } from './ComparisonView';
import { ExplorationMapView } from './ExplorationMapView';
import { ProsConsView } from './ProsConsView';
import { ConstraintListView } from './ConstraintListView';
import { FlowView } from './FlowView';
import { ConceptMapView } from './ConceptMapView';
import { GenericView } from './GenericView';
import type {
  AssumptionSurfaceContent,
  AngleMapContent,
  DecisionTreeContent,
  ChecklistContent,
  ComparisonContent,
  ExplorationMapContent,
  ProsConsContent,
  ConstraintListContent,
  FlowContent,
  ConceptMapContent,
} from './types';

interface StructureContentProps {
  type: StructureType;
  content: Record<string, unknown>;
}

export const StructureContent = memo(function StructureContent({
  type,
  content,
}: StructureContentProps) {
  switch (type) {
    case 'assumption_surface':
      return <AssumptionSurfaceView content={content as AssumptionSurfaceContent} />;
    case 'angle_map':
      return <AngleMapView content={content as AngleMapContent} />;
    case 'decision_tree':
      return <DecisionTreeView content={content as DecisionTreeContent} />;
    case 'checklist':
      return <ChecklistView content={content as ChecklistContent} />;
    case 'comparison':
      return <ComparisonView content={content as ComparisonContent} />;
    case 'exploration_map':
      return <ExplorationMapView content={content as ExplorationMapContent} />;
    case 'pros_cons':
      return <ProsConsView content={content as ProsConsContent} />;
    case 'constraint_list':
      return <ConstraintListView content={content as ConstraintListContent} />;
    case 'flow':
      return <FlowView content={content as FlowContent} />;
    case 'concept_map':
      return <ConceptMapView content={content as ConceptMapContent} />;
    default:
      return <GenericView content={content} />;
  }
});
