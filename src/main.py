import solara
import src.state as state
from src.config import APP_TITLE, STEP1_NAV_LABEL, STEP2_NAV_LABEL

# Import Pages
from src.step1.app import Page as Step1Page
from src.step2.app import Page as Step2Page


@solara.component
def Page():
    current = state.current_step.value

    # AppBar with navigation
    with solara.AppBarTitle():
        solara.Text(APP_TITLE)

    # Navigation buttons in AppBar
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

    # Page content based on current step
    if current == 1:
        Step1Page()
    elif current == 2:
        Step2Page()
    else:
        solara.Error(f"Unknown Step: {current}")


if __name__ == "__main__":
    Page()
