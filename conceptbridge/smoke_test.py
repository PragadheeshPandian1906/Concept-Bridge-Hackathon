from pydantic import BaseModel
from slice.llm import complete


class Ping(BaseModel):
    ok: bool
    model_says: str


print(
    complete(
        messages=[
            {
                "role": "user",
                "content": 'Return JSON {"ok":true,"model_says":"hello"}',
            }
        ],
        schema=Ping,
        step="smoke",
    )
)