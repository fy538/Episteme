"""
Skill preview service

Analyzes a case to preview what skill would be created from it.
"""
from typing import Dict, List, Any
from collections import Counter
from apps.cases.models import Case
from apps.signals.models import Signal


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
        
        # Extract signal type patterns
        signals = case.signals.all()
        signal_type_counts = Counter(s.type for s in signals)
        
        for signal_type, count in signal_type_counts.most_common():
            if count >= 2:  # Only include types used 2+ times
                signal_examples = signals.filter(type=signal_type)[:2]
                preview['signal_types'].append({
                    'name': signal_type,
                    'count': count,
                    'examples': [s.text for s in signal_examples]
                })
        
        # Extract evidence patterns
        try:
            from apps.projects.models import Evidence
            evidence = Evidence.objects.filter(document__case=case)
            
            if evidence.exists():
                avg_credibility = evidence.aggregate(
                    models.Avg('extraction_confidence')
                )['extraction_confidence__avg'] or 0.0
                
                preview['evidence_patterns'] = {
                    'total_evidence': evidence.count(),
                    'avg_credibility': round(avg_credibility, 2),
                    'common_sources': []  # Could extract from citations
                }
        except Exception:
            # Evidence app might not be available yet
            preview['evidence_patterns'] = {
                'total_evidence': 0,
                'avg_credibility': 0.0,
                'common_sources': []
            }
        
        # Generate workflow template from artifacts
        try:
            from apps.artifacts.models import Artifact
            artifacts = case.artifacts.all()
            
            workflow_steps = []
            if artifacts.filter(type='research').exists():
                workflow_steps.append("1. Conduct research")
            if artifacts.filter(type='critique').exists():
                workflow_steps.append("2. Challenge assumptions")
            if artifacts.filter(type='brief').exists():
                workflow_steps.append("3. Generate decision brief")
            
            if workflow_steps:
                preview['workflow_template'] = '\n'.join(workflow_steps)
            else:
                preview['workflow_template'] = (
                    "1. Identify key signals\n"
                    "2. Gather evidence\n"
                    "3. Analyze and synthesize\n"
                    "4. Generate artifacts"
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
            'total_signals': signals.count(),
            'unique_signal_types': len(signal_type_counts),
            'confirmed_signals': signals.filter(status='confirmed').count(),
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
        signals = case.signals.all()
        
        if signals.count() < 3:
            return False, "Need at least 3 signals to create a skill"
        
        if not case.position or len(case.position) < 20:
            return False, "Case needs a position/thesis"
        
        return True, "Case is ready to become a skill"
