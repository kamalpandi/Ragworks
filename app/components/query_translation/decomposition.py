from .base import BaseQueryTranslator


class MultiQueryTranslator(BaseQueryTranslator):
    async def translate(self, query: str) -> list[str]:
        prompt = self.user_prompt_template.format(query=query)

        response = await self.llm.complete(prompt=prompt, system=self.system_prompt)

        return [q.strip() for q in response.content.split("\n") if q.strip()]


class StepBackTranslator(BaseQueryTranslator):
    async def translate(self, query: str) -> list[str]:
        prompt = self.user_prompt_template.format(query=query)

        step_back_question = await self.llm.complete(
            prompt=prompt, system=self.system_prompt
        )

        return [query, step_back_question.content.strip()]


class RagFusionTranslator(BaseQueryTranslator):
    async def translate(self, query: str) -> list[str]:
        prompt = self.user_prompt_template.format(query=query)

        response = await self.llm.complete(prompt=prompt, system=self.system_prompt)

        return [q.strip() for q in response.content.split("\n") if q.strip()]
