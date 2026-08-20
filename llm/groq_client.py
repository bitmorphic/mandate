import os
import json
from typing import List, Dict, Any
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class GroqClient:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-70b-versatile"
        
    def analyze_code(self, diff: str, system_prompt: str) -> List[Dict[str, Any]]:
        """
        Analyze the code diff using Groq LLM.
        Expected to return a list of findings.
        """
        prompt = f"""
You are an expert code reviewer. Analyze the following unified diff and report any issues.
Respond ONLY with a JSON object containing a "findings" key that holds an array of finding objects. 
Each object should have the following keys:
- "file": The file path where the issue was found.
- "line": The line number (or approximate line number) of the issue.
- "message": A descriptive message explaining the issue and how to fix it.
- "severity": One of "info", "warning", or "error".

If there are no issues, respond with: {{"findings": []}}

Diff to analyze:
```diff
{diff}
```
"""
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            if isinstance(parsed, dict) and "findings" in parsed:
                return parsed["findings"]
            
            return []
                
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return []
