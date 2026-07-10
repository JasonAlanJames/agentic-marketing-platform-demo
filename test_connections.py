import os
import sys

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langfuse import Langfuse


def require_environment_variable(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def main() -> None:
    load_dotenv()

    require_environment_variable("AWS_ACCESS_KEY_ID")
    require_environment_variable("AWS_SECRET_ACCESS_KEY")
    require_environment_variable("LANGFUSE_PUBLIC_KEY")
    require_environment_variable("LANGFUSE_SECRET_KEY")

    aws_region = os.getenv("AWS_REGION", "us-west-2")

    print("Environment variables loaded successfully.")

    langfuse = Langfuse()

    if not langfuse.auth_check():
        raise RuntimeError("Langfuse authentication failed.")

    print("Langfuse authentication succeeded.")

    model = ChatBedrockConverse(
        model_id="amazon.nova-lite-v1:0",
        region_name=aws_region,
        temperature=0.1,
        max_tokens=300,
    )

    response = model.invoke(
        "Reply with exactly two words: Bedrock works"
    )

    print("Bedrock response:")
    print(response.content)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nConnection test failed: {exc}", file=sys.stderr)
        raise