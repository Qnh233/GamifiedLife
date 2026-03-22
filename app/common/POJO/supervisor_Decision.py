from pydantic import BaseModel, Field

"""
Example output:
{"decision": "PLANNING", "reasoning": "User wants to create a new goal for their thesis", "confidence": 0.95}
"""
class Decision(BaseModel):
    decision: str = Field(description="计划的唯一标识符")
    reasoning: str = Field(description="对决策的简要解释")
    confidence: float = Field(description="从0到1的置信度评分")
