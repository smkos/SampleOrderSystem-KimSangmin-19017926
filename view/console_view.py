class ConsoleView:
    """콘솔 입출력만 담당한다. Controller를 호출하지 않는다."""

    def show_main_menu(self, summary: dict) -> None:
        print("=== S-Semi 시료 생산주문관리 시스템 ===")
        print(f"등록 시료 수: {summary['sample_count']}")
        print(f"총 재고: {summary['total_stock_qty']}")
        print(f"전체 주문 수: {summary['total_order_count']}")
        print(f"생산라인 대기 건수: {summary['pending_production_count']}")
        print("1. 시료 관리")
        print("2. 시료 주문")
        print("3. 주문 승인/거절")
        print("4. 모니터링")
        print("5. 생산 라인")
        print("6. 출고 처리")
        print("7. 종료")

    def get_menu_choice(self) -> str:
        return input("메뉴를 선택하세요: ").strip()

    def show_sample_menu(self) -> None:
        print("=== 시료 관리 ===")
        print("1. 신규 등록")
        print("2. 목록 조회")
        print("3. 이름 검색")
        print("4. 뒤로 가기")

    def get_sample_menu_choice(self) -> str:
        return input("메뉴를 선택하세요: ").strip()

    def get_new_sample_input(self) -> dict:
        sample_id = input("시료 ID: ")
        name = input("이름: ")
        avg_production_time_min = float(input("평균 생산시간(분): "))
        yield_rate = float(input("수율: "))
        stock_qty = int(input("초기 재고 수량: "))
        return {
            "sample_id": sample_id,
            "name": name,
            "avg_production_time_min": avg_production_time_min,
            "yield_rate": yield_rate,
            "stock_qty": stock_qty,
        }

    def show_sample_registered(self, sample) -> None:
        print(f"시료가 등록되었습니다: {sample.sample_id} ({sample.name})")

    def show_sample_list(self, samples: list) -> None:
        if not samples:
            print("등록된 시료가 없습니다")
            return
        for sample in samples:
            print(f"{sample.sample_id} | {sample.name} | 재고: {sample.stock_qty}")

    def get_search_keyword(self) -> str:
        return input("검색어: ")

    def show_search_results(self, samples: list) -> None:
        if not samples:
            print("검색 결과가 없습니다")
            return
        for sample in samples:
            print(f"{sample.sample_id} | {sample.name} | 재고: {sample.stock_qty}")

    def get_new_order_input(self) -> dict:
        sample_id = input("시료 ID: ")
        customer_name = input("고객명: ")
        quantity = int(input("주문 수량: "))
        return {
            "sample_id": sample_id,
            "customer_name": customer_name,
            "quantity": quantity,
        }

    def show_order_created(self, order) -> None:
        print(f"주문이 접수되었습니다: {order.order_id} ({order.status.value})")

    def show_pending_orders(self, orders: list) -> None:
        if not orders:
            print("접수된 주문이 없습니다")
            return
        for order in orders:
            print(f"{order.order_id} | {order.sample_id} | {order.customer_name} | 수량: {order.quantity}")

    def get_order_id_to_process(self) -> str:
        return input("처리할 주문 ID: ").strip()

    def get_approval_decision(self) -> str:
        return input("1. 승인  2. 거절: ").strip()

    def show_order_approved(self, order) -> None:
        print(f"주문이 승인되었습니다: {order.order_id} ({order.status.value})")

    def show_order_rejected(self, order) -> None:
        print(f"주문이 거절되었습니다: {order.order_id} ({order.status.value})")

    def show_monitoring_menu(self) -> None:
        print("=== 모니터링 ===")
        print("1. 주문량 확인")
        print("2. 재고량 확인")
        print("3. 뒤로 가기")

    def get_monitoring_menu_choice(self) -> str:
        return input("메뉴를 선택하세요: ").strip()

    def show_order_counts(self, counts: dict) -> None:
        for status, count in counts.items():
            print(f"{status.value}: {count}")

    def show_stock_status(self, labels: dict) -> None:
        for sample_id, label in labels.items():
            print(f"{sample_id}: {label}")

    def show_production_menu(self) -> None:
        print("=== 생산 라인 ===")
        print("1. 생산 현황 조회")
        print("2. 생산완료 처리")
        print("3. 뒤로 가기")

    def get_production_menu_choice(self) -> str:
        return input("메뉴를 선택하세요: ").strip()

    def show_current_production(self, order) -> None:
        if order is None:
            print("현재 생산 중인 주문이 없습니다")
            return
        print(f"{order.order_id} | {order.sample_id} | {order.customer_name} | 수량: {order.quantity}")

    def show_production_queue(self, orders: list) -> None:
        if not orders:
            print("대기 중인 생산 주문이 없습니다")
            return
        for order in orders:
            print(f"{order.order_id} | {order.sample_id} | {order.customer_name} | 수량: {order.quantity}")

    def get_order_id_to_complete(self) -> str:
        return input("생산완료 처리할 주문 ID: ").strip()

    def show_production_completed(self, order) -> None:
        print(f"생산이 완료되었습니다: {order.order_id} ({order.status.value})")
