from database import (
    init_db,
    init_teams,
    get_teams,
    get_proposals,
    confirm_stage,
)


def main():
    init_db()
    init_teams()

    print("Команды:")
    for team in get_teams():
        print(f"{team['name']} — {team['points']} баллов")

    try:
        task_id = int(input("\nНомер задачи: "))
        proposals = get_proposals(task_id)

        selected = [
            proposal
            for proposal in proposals
            if proposal["status"] == "accepted"
        ]

        if not selected:
            print("У задачи пока нет выбранных команд.")
            return

        print("\nВыбранные команды:")
        for proposal in selected:
            print(f"Отклик №{proposal['id']}: {proposal['team_name']}")

        proposal_id = int(input("\nНомер отклика: "))

        if proposal_id not in {proposal["id"] for proposal in selected}:
            raise ValueError("Выберите отклик из показанного списка.")

        description = input("Что команда фактически выполнила? ")

        answer = input("Бизнес подтверждает выполнение? Введите да: ")

        if answer.strip().lower() != "да":
            print("Подтверждение отменено. Баллы не начислены.")
            return

        points = confirm_stage(proposal_id, description)
        print(f"\nНачислено {points} баллов!")

        for team in get_teams():
            print(f"{team['name']} — {team['points']} баллов")

    except ValueError as error:
        print("Ошибка:", error)


if __name__ == "__main__":
    main()
