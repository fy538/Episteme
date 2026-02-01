"""
Skill parser for SKILL.md files with YAML frontmatter

Follows Anthropic's Agent Skills specification.
"""
import yaml
from typing import Dict, Tuple, List


def parse_skill_md(content: str) -> Dict:
    """
    Parse SKILL.md with YAML frontmatter and markdown body
    
    Expected format:
    ---
    name: Skill Name
    description: Skill description
    domain: domain_name
    episteme:
      applies_to_agents:
        - research
        - critique
      signal_types:
        - name: CustomType
          inherits_from: Constraint
    ---
    
    ## Markdown body content
    ...
    
    Args:
        content: Full SKILL.md file content
    
    Returns:
        {
            'metadata': dict,  # Parsed YAML frontmatter
            'body': str        # Markdown body
        }
    """
    lines = content.split('\n')
    
    # Check for YAML frontmatter
    if len(lines) < 3 or lines[0].strip() != '---':
        # No frontmatter, treat entire content as body
        return {
            'metadata': {},
            'body': content
        }
    
    # Find the closing ---
    try:
        yaml_end_idx = lines[1:].index('---') + 1
    except ValueError:
        # No closing ---, treat as plain markdown
        return {
            'metadata': {},
            'body': content
        }
    
    # Extract YAML and body
    yaml_content = '\n'.join(lines[1:yaml_end_idx])
    markdown_body = '\n'.join(lines[yaml_end_idx + 1:]).strip()
    
    try:
        metadata = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}")
    
    return {
        'metadata': metadata,
        'body': markdown_body
    }


def validate_skill_md(content: str) -> Tuple[bool, List[str]]:
    """
    Validate required fields in SKILL.md
    
    According to Anthropic spec, required fields are:
    - name (max 64 chars)
    - description (max 200 chars)
    
    Args:
        content: Full SKILL.md file content
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    try:
        parsed = parse_skill_md(content)
    except ValueError as e:
        return False, [str(e)]
    
    metadata = parsed['metadata']
    
    # Check required fields
    if 'name' not in metadata:
        errors.append("Missing required field: name")
    elif not isinstance(metadata['name'], str):
        errors.append("Field 'name' must be a string")
    elif len(metadata['name']) > 64:
        errors.append("Field 'name' exceeds maximum length of 64 characters")
    elif len(metadata['name'].strip()) == 0:
        errors.append("Field 'name' cannot be empty")
    
    if 'description' not in metadata:
        errors.append("Missing required field: description")
    elif not isinstance(metadata['description'], str):
        errors.append("Field 'description' must be a string")
    elif len(metadata['description']) > 200:
        errors.append("Field 'description' exceeds maximum length of 200 characters")
    elif len(metadata['description'].strip()) == 0:
        errors.append("Field 'description' cannot be empty")
    
    # Validate size limit (50KB)
    if len(content) > 50 * 1024:
        errors.append("SKILL.md exceeds maximum size of 50KB")
    
    # Validate episteme config if present
    if 'episteme' in metadata:
        episteme = metadata['episteme']
        if not isinstance(episteme, dict):
            errors.append("Field 'episteme' must be an object")
        else:
            # Validate applies_to_agents if present
            if 'applies_to_agents' in episteme:
                agents = episteme['applies_to_agents']
                if not isinstance(agents, list):
                    errors.append("Field 'episteme.applies_to_agents' must be a list")
                else:
                    valid_agents = ['research', 'critique', 'brief', 'extract']
                    for agent in agents:
                        if agent not in valid_agents:
                            errors.append(
                                f"Invalid agent type '{agent}'. "
                                f"Must be one of: {', '.join(valid_agents)}"
                            )
    
    return len(errors) == 0, errors


def extract_metadata_from_yaml(content: str) -> Dict:
    """
    Extract just the metadata without full parsing
    
    Useful for quick checks without processing the full body.
    
    Args:
        content: Full SKILL.md file content
    
    Returns:
        Metadata dict or empty dict if no frontmatter
    """
    parsed = parse_skill_md(content)
    return parsed['metadata']


def validate_resource_files(resources: Dict) -> Tuple[bool, List[str]]:
    """
    Validate resource files attached to a skill
    
    Args:
        resources: Dict of {filename: content}
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    if not isinstance(resources, dict):
        return False, ["Resources must be a dictionary of {filename: content}"]
    
    total_size = 0
    
    for filename, content in resources.items():
        if not isinstance(filename, str):
            errors.append("Resource filename must be a string")
            continue
        
        if not isinstance(content, str):
            errors.append(f"Resource content for '{filename}' must be a string")
            continue
        
        # Check individual file size
        file_size = len(content.encode('utf-8'))
        total_size += file_size
        
        if file_size > 2 * 1024 * 1024:  # 2MB per file
            errors.append(f"Resource file '{filename}' exceeds 2MB limit")
    
    # Check total size
    if total_size > 5 * 1024 * 1024:  # 5MB total
        errors.append("Total resource files exceed 5MB limit")
    
    return len(errors) == 0, errors
