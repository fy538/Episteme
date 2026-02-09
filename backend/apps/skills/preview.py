"""
Skill preview service

Analyzes a case to preview what skill would be created from it.
"""
from typing import Dict, List, Any
from apps.cases.models import Case


class SkillPreviewService:
    """Generate preview of skill that would be created from a case"""
    
    @staticmethod
    def analyze_case(case: Case) -> Dict[str, Any]:
        """
        Analyze case and extract skill-worthy patterns
        
        Args:
            case: Case to analyze
        
        Returns:
            {
                'signal_types': [...],
                'evidence_patterns': {...},
                'workflow_template': str,
                'suggested_name': str,
                'suggested_description': str,
                'domain_suggestions': [...],
                'stats': {...}
            }
        """
        preview = {
            'signal_types': [],
            'evidence_patterns': {},
            'workflow_template': '',
            'suggested_name': '',
            'suggested_description': '',
            'domain_suggestions': [],
            'stats': {}
        }
        
        # Signal model has been removed. Signal type patterns are no longer available.
        # TODO: Extract patterns from graph nodes instead.
        
        # Extract evidence patterns from graph nodes
        try:
            from apps.graph.models import Node, NodeType
            from django.db.models import Avg
            evidence_nodes = Node.objects.filter(
                project=case.project,
                node_type=NodeType.EVIDENCE,
            )

            if evidence_nodes.exists():
                avg_confidence = evidence_nodes.aggregate(
                    Avg('confidence')
                )['confidence__avg'] or 0.0

                preview['evidence_patterns'] = {
                    'total_evidence': evidence_nodes.count(),
                    'avg_credibility': round(avg_confidence, 2),
                    'common_sources': []  # Could extract from node.properties
                }
        except Exception:
            preview['evidence_patterns'] = {
                'total_evidence': 0,
                'avg_credibility': 0.0,
                'common_sources': []
            }
        
        # Generate workflow template from working documents
        try:
            from apps.cases.models import WorkingDocument
            documents = case.working_documents.all()

            workflow_steps = []
            if documents.filter(document_type='research').exists():
                workflow_steps.append("1. Conduct research")
            if documents.filter(document_type='case_brief').exists():
                workflow_steps.append("2. Generate decision brief")

            if workflow_steps:
                preview['workflow_template'] = '\n'.join(workflow_steps)
            else:
                preview['workflow_template'] = (
                    "1. Identify key claims\n"
                    "2. Gather evidence\n"
                    "3. Analyze and synthesize\n"
                    "4. Generate documents"
                )
        except Exception:
            preview['workflow_template'] = (
                "1. Identify key signals\n"
                "2. Gather evidence\n"
                "3. Analyze and synthesize"
            )
        
        # Suggest name based on case title
        preview['suggested_name'] = f"{case.title} Framework"
        if len(preview['suggested_name']) > 64:
            preview['suggested_name'] = case.title[:60] + "..."
        
        # Suggest description
        preview['suggested_description'] = f"Template for analyzing {case.title.lower()}"
        if len(preview['suggested_description']) > 200:
            preview['suggested_description'] = preview['suggested_description'][:197] + "..."
        
        # Suggest domains based on case metadata
        if case.project:
            preview['domain_suggestions'].append(case.project.name.lower())
        
        # Add position as domain hint
        position_words = case.position.lower().split()[:3]
        for word in ['legal', 'medical', 'product', 'technical', 'financial']:
            if word in position_words:
                preview['domain_suggestions'].append(word)
        
        # Stats
        preview['stats'] = {
            'total_artifacts': 0
        }
        
        try:
            preview['stats']['total_artifacts'] = case.artifacts.count()
        except Exception:
            pass
        
        return preview
    
    @staticmethod
    def can_create_skill(case: Case) -> tuple[bool, str]:
        """
        Check if a case has enough content to create a meaningful skill
        
        Args:
            case: Case to check
        
        Returns:
            (can_create, reason)
        """
        if not case.position or len(case.position) < 20:
            return False, "Case needs a position/thesis"
        
        return True, "Case is ready to become a skill"
