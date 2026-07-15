from pathlib import Path

from controller.monitoring_controller import MonitoringController
from controller.order_controller import OrderController
from controller.production_controller import ProductionController
from controller.sample_controller import SampleController
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry
from storage.order_repository import OrderRepository
from storage.sample_repository import SampleRepository
from view.console_view import ConsoleView

SAMPLES_PATH = Path("samples.json")
ORDERS_PATH = Path("orders.json")


def build_controllers(samples_path, orders_path) -> tuple:
    sample_repository = SampleRepository(samples_path)
    order_repository = OrderRepository(orders_path)
    sample_registry = SampleRegistry()
    order_registry = OrderRegistry()

    sample_controller = SampleController(sample_registry, sample_repository)
    order_controller = OrderController(
        order_registry, sample_registry, order_repository, sample_repository
    )
    production_controller = ProductionController(
        order_registry, sample_registry, order_repository, sample_repository
    )
    monitoring_controller = MonitoringController(order_registry, sample_registry)

    return sample_controller, order_controller, production_controller, monitoring_controller


def build_summary(sample_controller, order_controller, production_controller) -> dict:
    samples = sample_controller.list_samples()
    return {
        "sample_count": len(samples),
        "total_stock_qty": sum(sample.stock_qty for sample in samples),
        "total_order_count": len(order_controller.list_orders()),
        "pending_production_count": len(production_controller.list_production_queue()),
    }


def _run_sample_menu(view, sample_controller) -> None:
    while True:
        view.show_sample_menu()
        choice = view.get_sample_menu_choice()
        if choice == "1":
            try:
                sample_input = view.get_new_sample_input()
                sample = Sample(**sample_input)
                sample_controller.register_sample(sample)
                view.show_sample_registered(sample)
            except ValueError as e:
                view.show_error(str(e))
        elif choice == "2":
            view.show_sample_list(sample_controller.list_samples())
        elif choice == "3":
            keyword = view.get_search_keyword()
            view.show_search_results(sample_controller.search_samples(keyword))
        elif choice == "4":
            return


def _run_order_menu(view, order_controller) -> None:
    try:
        order_input = view.get_new_order_input()
        order = order_controller.create_order(**order_input)
        view.show_order_created(order)
    except ValueError as e:
        view.show_error(str(e))


def _run_approval_menu(view, order_controller) -> None:
    try:
        view.show_pending_orders(order_controller.list_pending_orders())
        order_id = view.get_order_id_to_process()
        decision = view.get_approval_decision()
        if decision == "1":
            order = order_controller.approve_order(order_id)
            view.show_order_approved(order)
        elif decision == "2":
            order = order_controller.reject_order(order_id)
            view.show_order_rejected(order)
        else:
            print("잘못된 선택입니다")
    except ValueError as e:
        view.show_error(str(e))


def _run_monitoring_menu(view, monitoring_controller) -> None:
    while True:
        view.show_monitoring_menu()
        choice = view.get_monitoring_menu_choice()
        if choice == "1":
            view.show_order_counts(monitoring_controller.count_orders_by_status())
        elif choice == "2":
            view.show_stock_status(monitoring_controller.stock_status_by_sample())
        elif choice == "3":
            return


def _run_production_menu(view, production_controller) -> None:
    while True:
        view.show_production_menu()
        choice = view.get_production_menu_choice()
        if choice == "1":
            view.show_current_production(production_controller.current_production_order())
            view.show_production_queue(production_controller.list_production_queue())
        elif choice == "2":
            try:
                order_id = view.get_order_id_to_complete()
                order = production_controller.complete_production(order_id)
                view.show_production_completed(order)
            except ValueError as e:
                view.show_error(str(e))
        elif choice == "3":
            return


def _run_release_menu(view, order_controller) -> None:
    try:
        view.show_releasable_orders(order_controller.list_releasable_orders())
        order_id = view.get_order_id_to_release()
        order = order_controller.release_order(order_id)
        view.show_order_released(order)
    except ValueError as e:
        view.show_error(str(e))


def run_main_loop(
    view, sample_controller, order_controller, production_controller, monitoring_controller
) -> None:
    while True:
        summary = build_summary(sample_controller, order_controller, production_controller)
        view.show_main_menu(summary)
        choice = view.get_menu_choice()
        if choice == "1":
            _run_sample_menu(view, sample_controller)
        elif choice == "2":
            _run_order_menu(view, order_controller)
        elif choice == "3":
            _run_approval_menu(view, order_controller)
        elif choice == "4":
            _run_monitoring_menu(view, monitoring_controller)
        elif choice == "5":
            _run_production_menu(view, production_controller)
        elif choice == "6":
            _run_release_menu(view, order_controller)
        elif choice == "7":
            return


def main() -> None:
    controllers = build_controllers(SAMPLES_PATH, ORDERS_PATH)
    run_main_loop(ConsoleView(), *controllers)


if __name__ == "__main__":
    main()
