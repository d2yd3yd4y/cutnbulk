document.addEventListener("DOMContentLoaded", () => {
  bindMealTemplates();
  bindWorkoutRows();
});

function bindMealTemplates() {
  const description = document.querySelector("#meal-description");
  if (!description) return;

  document.querySelectorAll("[data-template]").forEach((button) => {
    button.addEventListener("click", () => {
      description.value = button.dataset.template || "";
      description.focus();
    });
  });
}

function bindWorkoutRows() {
  const container = document.querySelector("#workout-rows");
  const addButton = document.querySelector("#add-workout-row");
  if (!container || !addButton) return;

  addButton.addEventListener("click", () => {
    const firstRow = container.querySelector(".workout-row");
    if (!firstRow) return;

    const row = firstRow.cloneNode(true);
    row.querySelectorAll("input").forEach((input) => {
      if (input.type === "checkbox") {
        input.checked = false;
      } else if (input.name === "sets") {
        input.value = "3";
      } else if (input.name === "reps") {
        input.value = "10";
      } else if (input.name === "weight_kg") {
        input.value = "0";
      } else {
        input.value = "";
      }
    });
    container.appendChild(row);
    refreshFailureIndexes(container);
  });

  container.addEventListener("change", () => refreshFailureIndexes(container));
  refreshFailureIndexes(container);
}

function refreshFailureIndexes(container) {
  container.querySelectorAll(".workout-row").forEach((row, index) => {
    const checkbox = row.querySelector('input[name="to_failure"]');
    if (checkbox) checkbox.value = String(index);
  });
}
