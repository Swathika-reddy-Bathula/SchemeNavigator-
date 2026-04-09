from langchain_core.messages import AIMessage, HumanMessage


class SimpleConversationMemory:
    def __init__(self, return_messages: bool = True):
        self.return_messages = return_messages
        self.history = []

    def load_memory_variables(self, _inputs):
        if self.return_messages:
            return {"history": self.history}
        return {
            "history": "\n".join(
                f"Human: {msg.content}" if isinstance(msg, HumanMessage) else f"AI: {msg.content}"
                for msg in self.history
            )
        }

    def save_context(self, inputs, outputs):
        user_input = inputs.get("input")
        assistant_output = outputs.get("output")

        if user_input:
            self.history.append(HumanMessage(content=user_input))
        if assistant_output:
            self.history.append(AIMessage(content=assistant_output))
