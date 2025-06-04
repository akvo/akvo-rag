from utils.rag_util import (
    rag_register_user,
)


def main():
    print("=== Create or Update User ===")
    email = input("Email: ")
    is_super_user = input("Is Super User? (y/n): ").lower() == "y"
    rag_register_user(
        is_super_user=is_super_user,
        email=email,
        username=email,
        password=email,
        create_or_update=True,
    )


if __name__ == "__main__":
    main()
