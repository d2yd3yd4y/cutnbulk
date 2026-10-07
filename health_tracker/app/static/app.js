document.addEventListener("DOMContentLoaded", () => {
  bindMealTemplates();
  bindWorkoutRows();
  bindTrainingParts();
  bindMealForms();
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

function bindTrainingParts() {
  const inputs = Array.from(document.querySelectorAll('input[name="training_parts"]'));
  if (!inputs.length) return;

  inputs.forEach((input) => {
    input.addEventListener("change", () => {
      if (input.value === "休息" && input.checked) {
        inputs.forEach((item) => {
          if (item.value !== "休息") item.checked = false;
        });
      } else if (input.checked) {
        const rest = inputs.find((item) => item.value === "休息");
        if (rest) rest.checked = false;
      }
    });
  });
}

function bindMealForms() {
  document.querySelectorAll(".meal-form").forEach((form) => {
    bindMealTypeField(form);
    bindEntryMode(form);
    bindPhotoPreview(form);
  });
}

function bindMealTypeField(form) {
  const select = form.querySelector(".meal-type-select");
  const customField = form.querySelector(".custom-meal-name");
  const customInput = customField ? customField.querySelector('input[name="meal_name"]') : null;
  if (!select || !customField) return;

  const sync = () => {
    const isCustom = select.value === "custom";
    customField.hidden = !isCustom;
    if (!isCustom && customInput) {
      customInput.value = "";
    }
  };
  select.addEventListener("change", sync);
  sync();
}

function bindEntryMode(form) {
  const modeInputs = Array.from(form.querySelectorAll(".entry-mode-input"));
  if (!modeInputs.length) return;

  const sync = () => {
    const mode = modeInputs.find((input) => input.checked)?.value || "manual";
    form.dataset.entryMode = mode;

    form.querySelectorAll("[data-mode-panel]").forEach((panel) => {
      const active = panel.dataset.modePanel === mode;
      panel.hidden = !active;
      panel.querySelectorAll("input, textarea, select").forEach((field) => {
        field.disabled = !active;
      });
    });

    const description = form.querySelector(".meal-description-input");
    const manualLabel = form.querySelector(".desc-label-manual");
    const photoLabel = form.querySelector(".desc-label-photo");
    if (description) {
      const isManual = mode === "manual";
      description.required = isManual;
      description.placeholder =
        description.dataset[isManual ? "placeholderManual" : "placeholderPhoto"] ||
        description.placeholder;
      if (manualLabel) manualLabel.hidden = !isManual;
      if (photoLabel) photoLabel.hidden = isManual;
    }

    const imageInput = form.querySelector(".meal-image-input");
    if (imageInput) {
      imageInput.required = mode === "photo" && !form.querySelector(".photo-preview-img[src]");
    }
  };

  modeInputs.forEach((input) => input.addEventListener("change", sync));
  sync();
}

function bindPhotoPreview(form) {
  const imageInput = form.querySelector(".meal-image-input");
  if (!imageInput) return;

  imageInput.addEventListener("change", () => {
    const file = imageInput.files && imageInput.files[0];
    const wrap = form.querySelector(".photo-preview-wrap");
    let preview = form.querySelector(".photo-preview-link");
    let img = form.querySelector(".photo-preview-img");
    if (!wrap) return;

    if (!file) {
      if (preview && !preview.getAttribute("href")) {
        preview.hidden = true;
        if (img) img.removeAttribute("src");
      }
      return;
    }

    if (!preview) {
      preview = document.createElement("div");
      preview.className = "food-thumb photo-preview-link";
      img = document.createElement("img");
      img.className = "photo-preview-img";
      img.alt = "照片预览";
      preview.appendChild(img);
      wrap.prepend(preview);
    }

    if (!img) {
      img = document.createElement("img");
      img.className = "photo-preview-img";
      img.alt = "照片预览";
      preview.appendChild(img);
    }

    const url = URL.createObjectURL(file);
    img.onload = () => URL.revokeObjectURL(url);
    img.onerror = () => {
      preview.hidden = true;
      URL.revokeObjectURL(url);
    };
    img.src = url;
    preview.hidden = false;
    imageInput.required = false;
  });
}
