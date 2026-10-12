document.addEventListener("DOMContentLoaded", () => {
  bindMealTemplates();
  bindWorkoutRows();
  bindTrainingParts();
  bindMealTypeFields();
  bindMealImagePreviews();
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

function bindMealTypeFields() {
  document.querySelectorAll(".meal-form").forEach((form) => {
    const select = form.querySelector(".meal-type-select");
    const customField = form.querySelector(".custom-meal-name");
    if (!select || !customField) return;

    const sync = () => {
      customField.hidden = select.value !== "custom";
    };
    select.addEventListener("change", sync);
    sync();
  });
}

function bindMealImagePreviews() {
  document.querySelectorAll(".meal-form").forEach((form) => {
    const input = form.querySelector(".meal-image-input");
    const card = form.querySelector(".image-preview-card");
    const preview = form.querySelector(".image-preview");
    const nameLabel = form.querySelector(".image-preview-name");
    const placeholder = form.querySelector(".image-preview-placeholder");
    if (!input || !preview || !card) return;

    const showPreview = (src, labelText) => {
      preview.src = src;
      preview.style.display = "block";
      card.classList.add("has-image");
      if (placeholder) placeholder.style.display = "none";
      if (nameLabel) nameLabel.textContent = labelText || "";
    };

    const clearPreview = () => {
      const savedSrc = preview.dataset.savedSrc;
      if (savedSrc) {
        showPreview(savedSrc, "当前已保存照片");
        return;
      }
      preview.removeAttribute("src");
      preview.style.display = "none";
      card.classList.remove("has-image");
      if (placeholder) placeholder.style.display = "block";
      if (nameLabel) nameLabel.textContent = "";
    };

    if (preview.getAttribute("src")) {
      preview.dataset.savedSrc = preview.getAttribute("src");
      showPreview(preview.dataset.savedSrc, "当前已保存照片");
    } else {
      clearPreview();
    }

    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      if (!file) {
        clearPreview();
        return;
      }
      if (!file.type.startsWith("image/")) {
        clearPreview();
        if (nameLabel) nameLabel.textContent = "请选择图片文件";
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        showPreview(String(reader.result), `已选择：${file.name}`);
      };
      reader.onerror = () => {
        clearPreview();
        if (nameLabel) nameLabel.textContent = "预览失败，请重试";
      };
      reader.readAsDataURL(file);
    });
  });
}
