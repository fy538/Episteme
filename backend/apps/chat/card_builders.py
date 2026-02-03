"""
Service for building rich message cards
"""
from typing import List, Optional
from .cards import (
    SignalExtractionCard, 
    CaseSuggestionCard, 
    StructurePreviewCard,
    AssumptionValidatorCard,
    ResearchStatusCard,
    ActionPromptCard,
    CardAction
)


class CardBuilder:
    """Builds rich message cards"""
    
    @staticmethod
    def build_signal_extraction_card(signals: List) -> dict:
        """
        Build a signal extraction card
        
        Args:
            signals: List of Signal objects
            
        Returns:
            Dict ready for structured_content field
        """
        # Group signals by type
        by_type = {
            'assumption': [],
            'question': [],
            'evidence': [],
            'claim': []
        }
        for signal in signals:
            by_type.get(signal.type, []).append({
                'id': str(signal.id),
                'text': signal.text,
                'confidence': signal.confidence,
                'status': 'unvalidated'  # New field for tracking
            })
        
        # Build actions
        actions = []
        if by_type['assumption']:
            actions.append(CardAction(
                id='validate_assumptions',
                label=f"Validate {len(by_type['assumption'])} Assumption{'s' if len(by_type['assumption']) > 1 else ''}",
                action_type='validate_assumptions',
                payload={'signal_ids': [s['id'] for s in by_type['assumption']]},
                variant='primary'
            ))
        
        if by_type['question']:
            actions.append(CardAction(
                id='organize_questions',
                label=f"Organize {len(by_type['question'])} Question{'s' if len(by_type['question']) > 1 else ''}",
                action_type='organize_questions',
                payload={'signal_ids': [s['id'] for s in by_type['question']]},
                variant='secondary'
            ))
        
        card = SignalExtractionCard(
            heading=f"{len(signals)} Signal{'s' if len(signals) > 1 else ''} Detected",
            description="Key elements extracted from the conversation",
            signals=[
                {'type': k, 'items': v} 
                for k, v in by_type.items() if v
            ],
            actions=[a.model_dump() for a in actions],
            metadata={
                'total_count': len(signals),
                'by_type': {k: len(v) for k, v in by_type.items()}
            }
        )
        
        return card.model_dump()
    
    @staticmethod
    def build_assumption_validator_card(assumptions: List, research_results: Optional[dict] = None) -> dict:
        """
        Build an assumption validation card
        
        Args:
            assumptions: List of assumption signals
            research_results: Optional research data for each assumption
            
        Returns:
            Dict ready for structured_content field
        """
        assumption_items = []
        for assumption in assumptions:
            item = {
                'id': str(assumption.id),
                'text': assumption.text,
                'status': 'pending',  # pending, validated, refuted, uncertain
                'confidence': None,
                'supporting_evidence': [],
                'contradicting_evidence': []
            }
            
            # If we have research results, populate validation
            if research_results and str(assumption.id) in research_results:
                result = research_results[str(assumption.id)]
                item.update({
                    'status': result.get('status'),
                    'confidence': result.get('confidence'),
                    'supporting_evidence': result.get('supporting', []),
                    'contradicting_evidence': result.get('contradicting', [])
                })
            
            assumption_items.append(item)
        
        # Build actions based on validation state
        actions = []
        pending = [a for a in assumption_items if a['status'] == 'pending']
        if pending:
            actions.append(CardAction(
                id='research_assumptions',
                label=f"Research {len(pending)} Assumption{'s' if len(pending) > 1 else ''}",
                action_type='research_assumptions',
                payload={'assumption_ids': [a['id'] for a in pending]},
                variant='primary'
            ))
        
        validated = [a for a in assumption_items if a['status'] == 'validated']
        if validated:
            actions.append(CardAction(
                id='add_to_case',
                label=f"Add {len(validated)} to Case",
                action_type='add_validated_to_case',
                payload={'assumption_ids': [a['id'] for a in validated]},
                variant='secondary'
            ))
        
        card = AssumptionValidatorCard(
            heading="Assumption Validation",
            description=f"{len(assumption_items)} assumption{'s' if len(assumption_items) > 1 else ''} detected - validate to strengthen your argument",
            assumptions=assumption_items,
            actions=[a.model_dump() for a in actions],
            metadata={
                'pending_count': len(pending),
                'validated_count': len(validated)
            }
        )
        
        return card.model_dump()
    
    @staticmethod
    def build_action_prompt_card(
        prompt_type: str,
        detected_context: dict
    ) -> dict:
        """
        Build an action prompt card based on detected patterns
        
        Args:
            prompt_type: Type of prompt (e.g., 'organize_questions', 'create_case')
            detected_context: Context that triggered the prompt
            
        Returns:
            Dict ready for structured_content field
        """
        prompts = {
            'organize_questions': {
                'heading': "Organize Your Questions?",
                'description': f"You've asked {detected_context.get('question_count', 0)} questions. Create an inquiry to track answers systematically.",
                'priority': 'medium',
                'actions': [
                    CardAction(
                        id='create_inquiry',
                        label='Create Inquiry',
                        action_type='create_inquiry_from_questions',
                        payload=detected_context,
                        variant='primary'
                    ),
                    CardAction(
                        id='dismiss',
                        label='Not Now',
                        action_type='dismiss_suggestion',
                        payload={'type': 'organize_questions'},
                        variant='secondary'
                    )
                ]
            },
            'validate_assumptions': {
                'heading': "Validate Your Assumptions?",
                'description': f"I detected {detected_context.get('assumption_count', 0)} assumptions. Research can help validate or refute them.",
                'priority': 'high',
                'actions': [
                    CardAction(
                        id='validate',
                        label='Start Validation',
                        action_type='validate_assumptions',
                        payload=detected_context,
                        variant='primary'
                    ),
                    CardAction(
                        id='dismiss',
                        label='Skip',
                        action_type='dismiss_suggestion',
                        payload={'type': 'validate_assumptions'},
                        variant='secondary'
                    )
                ]
            },
            'create_case': {
                'heading': "Ready to Create a Case?",
                'description': "I've detected enough structure in our discussion to create a case with pre-filled content.",
                'priority': 'medium',
                'actions': [
                    CardAction(
                        id='create_case',
                        label='Create Case',
                        action_type='create_case_from_thread',
                        payload=detected_context,
                        variant='primary'
                    ),
                    CardAction(
                        id='preview',
                        label='Preview Structure',
                        action_type='preview_case_structure',
                        payload=detected_context,
                        variant='secondary'
                    )
                ]
            }
        }
        
        prompt_config = prompts.get(prompt_type, {
            'heading': 'Suggestion',
            'description': 'A suggestion based on your conversation',
            'priority': 'low',
            'actions': []
        })
        
        card = ActionPromptCard(
            heading=prompt_config['heading'],
            description=prompt_config['description'],
            prompt_type=prompt_type,
            priority=prompt_config.get('priority', 'medium'),
            actions=[a.model_dump() for a in prompt_config['actions']],
            metadata=detected_context
        )
        
        return card.model_dump()
    
    @staticmethod
    def build_research_status_card(
        agent_type: str,
        status: str,
        progress_steps: List[dict],
        results_preview: Optional[str] = None
    ) -> dict:
        """
        Build a research status card
        
        Args:
            agent_type: Type of agent running
            status: Current status (running, completed, failed)
            progress_steps: List of steps with status
            results_preview: Optional preview of results
            
        Returns:
            Dict ready for structured_content field
        """
        actions = []
        
        if status == 'running':
            actions.append(CardAction(
                id='stop',
                label='Stop Research',
                action_type='stop_agent',
                payload={'agent_type': agent_type},
                variant='danger'
            ))
        elif status == 'completed':
            actions.append(CardAction(
                id='view_results',
                label='View Full Results',
                action_type='view_agent_results',
                payload={'agent_type': agent_type},
                variant='primary'
            ))
            actions.append(CardAction(
                id='apply',
                label='Apply to Case',
                action_type='apply_research_to_case',
                payload={'agent_type': agent_type},
                variant='secondary'
            ))
        
        card = ResearchStatusCard(
            heading=f"{agent_type.capitalize()} Agent: {status.capitalize()}",
            description=f"Agent is {'working on' if status == 'running' else 'finished'} your research task",
            agent_type=agent_type,
            status=status,
            progress_steps=progress_steps,
            results_preview=results_preview,
            actions=[a.model_dump() for a in actions],
            metadata={
                'started_at': progress_steps[0].get('timestamp') if progress_steps else None,
                'step_count': len(progress_steps)
            }
        )
        
        return card.model_dump()
    
    @staticmethod
    def build_contradiction_card(
        contradiction: dict,
        priority: str = 'high'
    ) -> dict:
        """
        Build a contradiction detection card.
        
        Args:
            contradiction: Dict with evidence, contradicts info
            priority: Card priority (high/medium/low)
        
        Returns:
            Dict ready for structured_content field
        """
        evidence_text = contradiction.get('evidence_text', '')
        contradicts_text = contradiction.get('contradicts_text', '')
        confidence = contradiction.get('confidence', 0.0)
        
        heading = "Contradiction Detected"
        description = (
            f'"{evidence_text[:60]}..." contradicts '
            f'"{contradicts_text[:60]}..." '
            f'(Confidence: {int(confidence * 100)}%)'
        )
        
        actions = [
            CardAction(
                id='investigate_contradiction',
                label='Investigate',
                action_type='create_inquiry',
                payload={
                    'evidence_id': contradiction.get('evidence_id'),
                    'signal_id': contradiction.get('contradicts_id'),
                    'contradiction_data': contradiction
                },
                variant='primary'
            ),
            CardAction(
                id='dismiss_contradiction',
                label='Dismiss',
                action_type='dismiss_intervention',
                payload={'contradiction_id': contradiction.get('evidence_id')},
                variant='secondary'
            )
        ]
        
        return ActionPromptCard(
            heading=heading,
            description=description,
            prompt_type='resolve_contradiction',
            priority=priority,
            actions=actions,
            metadata={
                'contradiction': contradiction,
                'auto_detected': True
            }
        ).model_dump()
