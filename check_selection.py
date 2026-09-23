from database import init_db, get_proposals, set_proposal_status
from backend import get_catalog


def main():
    init_db()

    tasks = get_catalog()

    if not tasks:
        print("Нет опубликованных задач.")
        return

    print("Опубликованные задачи:")
    for task in tasks:
        print(f"№{task['id']}: {task['title']}")

    try:
        task_id = int(input("\nНомер задачи: "))
        proposals = get_proposals(task_id)

        if not proposals:
            print("У этой задачи пока нет откликов.")
            return

        print("\nОтклики:")
        for proposal in proposals:
            print(
                f"№{proposal['id']}: {proposal['team_name']} "
                f"— {proposal['status']}"
            )
            print("Идея:", proposal["idea"])
            print("План:", proposal["plan"])
            print("Срок:", proposal["deadline"])
            print("Прототип:", proposal["prototype_url"])
            print()

        proposal_id = int(input("Номер отклика для решения: "))

        # Не позволяем случайно изменить отклик другой задачи.
        valid_ids = {proposal["id"] for proposal in proposals}

        if proposal_id not in valid_ids:
            raise ValueError("Выберите отклик из показанного списка.")

        action = input("1 — выбрать команду, 2 — отклонить: ").strip()

        if action == "1":
            status = "accepted"
        elif action == "2":
            status = "rejected"
        else:
            raise ValueError("Нужно ввести 1 или 2.")

        set_proposal_status(proposal_id, status)

        print("\nРешение сохранено!")
        for proposal in get_proposals(task_id):
            print(
                f"№{proposal['id']}: {proposal['team_name']} "
                f"— {proposal['status']}"
            )

    except ValueError as error:
        print("Ошибка:", error)


if __name__ == "__main__":
    main()
