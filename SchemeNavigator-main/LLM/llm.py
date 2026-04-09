import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

class LLMClient:
    def __init__(self, model: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY. Add it to your .env file before starting the API.")

        self.client = Groq(api_key=api_key)
        self.model = model

    def run_chat(self, system_message: str, user_message: str) -> str:
        """Run a chat completion with the LLM and return the response"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error during LLM chat completion: {e}")
            return "Sorry, I couldn't get a response from the LLM at this time."
    
