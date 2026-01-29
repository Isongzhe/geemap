import sys
import solara
import src.state as state
from src.config import APP_TITLE, STEP1_NAV_LABEL, STEP2_NAV_LABEL

# 1. 直接在頂部匯入所有頁面
print("[MAIN] Starting imports...", flush=True)

from src.step1.app import Page as Step1Page
print("[MAIN] Step1 imported", flush=True)

from src.step2.app import Page as Step2Page
print("[MAIN] Step2 imported", flush=True)


@solara.component
def Page():
    print(f"[MAIN] Page() called", flush=True)
    current = state.current_step.value
    print(f"[MAIN] Current step: {current}", flush=True)

    # AppBar 導覽列
    with solara.AppBarTitle():
        solara.Text(APP_TITLE)

    with solara.AppBar():
        solara.Button(
            f"Step 1: {STEP1_NAV_LABEL}",
            on_click=lambda: state.current_step.set(1),
            outlined=current != 1,
            color="primary" if current == 1 else None,
        )
        solara.Button(
            f"Step 2: {STEP2_NAV_LABEL}",
            on_click=lambda: state.current_step.set(2),
            outlined=current != 2,
            color="primary" if current == 2 else None,
        )

    # 2. 直接根據狀態渲染，不再需要判斷是否已匯入
    if current == 1:
        print("[MAIN] Rendering Step1Page", flush=True)
        Step1Page()
    elif current == 2:
        print("[MAIN] Rendering Step2Page", flush=True)
        Step2Page()
    else:
        solara.Error(f"Unknown Step: {current}")


if __name__ == "__main__":
    Page()