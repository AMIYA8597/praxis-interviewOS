import re
from typing import Dict

class PromptBuilder:
    """
    A structured builder that emits explicitly fenced, labeled sections 
    to mitigate Prompt Injection. Never build a prompt by raw string concatenation.
    """
    
    def __init__(self):
        self.system_instructions = ""
        self.task = ""
        self.output_schema = ""
        self.candidate_facts = ""
        self.untrusted_documents = []
        self.untrusted_transcripts = []

    def set_system_instructions(self, instructions: str):
        self.system_instructions = instructions
        return self

    def set_task(self, task: str):
        self.task = task
        return self

    def set_output_schema(self, schema: str):
        self.output_schema = schema
        return self

    def set_candidate_facts(self, facts: str, verified: bool = True):
        v_str = "true" if verified else "false"
        self.candidate_facts = f"<CANDIDATE_FACTS verified={v_str}>\n{facts}\n</CANDIDATE_FACTS>"
        return self

    def _sanitize_untrusted(self, text: str, tag_name: str) -> str:
        """
        Escapes/strips closing tag sequences from untrusted content to prevent breakout.
        e.g., </UNTRUSTED_DOCUMENT> becomes <\\/UNTRUSTED_DOCUMENT>
        """
        # Case insensitive replacement for the closing tag
        pattern = re.compile(f"</{tag_name}>", re.IGNORECASE)
        sanitized = pattern.sub(f"<\\/{tag_name}>", text)
        
        # We also neutralize common injection vectors
        sanitized = sanitized.replace("</SYSTEM_INSTRUCTIONS>", "<\\/SYSTEM_INSTRUCTIONS>")
        sanitized = sanitized.replace("<SYSTEM_INSTRUCTIONS>", "<\\SYSTEM_INSTRUCTIONS>")
        return sanitized

    def add_untrusted_document(self, content: str, source: str = "unknown", page: int = 1):
        sanitized = self._sanitize_untrusted(content, "UNTRUSTED_DOCUMENT")
        block = f'<UNTRUSTED_DOCUMENT source="{source}" page="{page}">\n{sanitized}\n</UNTRUSTED_DOCUMENT>'
        self.untrusted_documents.append(block)
        return self

    def add_untrusted_transcript(self, content: str):
        sanitized = self._sanitize_untrusted(content, "UNTRUSTED_TRANSCRIPT")
        block = f'<UNTRUSTED_TRANSCRIPT>\n{sanitized}\n</UNTRUSTED_TRANSCRIPT>'
        self.untrusted_transcripts.append(block)
        return self

    def build(self) -> str:
        components = []
        
        if self.system_instructions:
            components.append(f"<SYSTEM_INSTRUCTIONS>\n{self.system_instructions}\n</SYSTEM_INSTRUCTIONS>")
        
        if self.task:
            components.append(f"<TASK>\n{self.task}\n</TASK>")
            
        if self.output_schema:
            components.append(f"<OUTPUT_SCHEMA>\n{self.output_schema}\n</OUTPUT_SCHEMA>")
            
        if self.candidate_facts:
            components.append(self.candidate_facts)
            
        if self.untrusted_documents:
            components.extend(self.untrusted_documents)
            
        if self.untrusted_transcripts:
            components.extend(self.untrusted_transcripts)
            
        return "\n\n".join(components)
