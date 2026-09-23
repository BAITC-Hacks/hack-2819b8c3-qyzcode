from backend import get_catalog
from database import init_db, create_proposal, get_proposals


def main():
    init_db()
    tasks = get_catalog()

    if not tasks:
        print("Сначала опубликуйте задачу через check_catalog.py.")
        return

    print("Доступные задачи:")
    for task in tasks:
        print(f"№{task['id']}: {task['title']}")

    try:
        task_id = int(input("\nНомер задачи: "))

        team_name = input("Название команды: ")
        idea = input("Идея решения: ")
        plan = input("План действий: ")
        deadline = input("Срок выполнения: ")
        prototype_url = input("Ссылка на прототип: ")

        proposal_id = create_proposal(
            task_id=task_id,
            team_name=team_name,
            idea=idea,
            plan=plan,
            deadline=deadline,
            prototype_url=prototype_url,
        )

    except ValueError as error:
        print("Ошибка:", error)
        return

    print(f"\nОтклик №{proposal_id} сохранён!")

    print("\nОтклики на эту задачу:")
    for proposal in get_proposals(task_id):
        print(
            f"№{proposal['id']}: {proposal['team_name']} "
            f"— {proposal['idea']} "
            f"— статус: {proposal['status']}"
        )


if __name__ == "__main__":
    main()