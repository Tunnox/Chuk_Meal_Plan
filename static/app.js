const state = {
  selectedDate: new Date().toISOString().slice(0, 10),
  meals: [],
  loading: false,
};

const mealGrid = document.querySelector("#mealGrid");
const datePicker = document.querySelector("#datePicker");
const selectedDateLabel = document.querySelector("#selectedDateLabel");
const feedbackMessage = document.querySelector("#feedbackMessage");
const totalMeals = document.querySelector("#totalMeals");
const completedMeals = document.querySelector("#completedMeals");
const template = document.querySelector("#mealCardTemplate");

document.querySelector("#todayBtn").addEventListener("click", () => {
  state.selectedDate = new Date().toISOString().slice(0, 10);
  syncDateControls();
  loadMeals();
});

document.querySelector("#previousDayBtn").addEventListener("click", () => {
  shiftDateBy(-1);
});

document.querySelector("#nextDayBtn").addEventListener("click", () => {
  shiftDateBy(1);
});

datePicker.addEventListener("change", (event) => {
  state.selectedDate = event.target.value;
  syncDateControls();
  loadMeals();
});

function shiftDateBy(days) {
  const selected = new Date(`${state.selectedDate}T00:00:00`);
  selected.setDate(selected.getDate() + days);
  state.selectedDate = selected.toISOString().slice(0, 10);
  syncDateControls();
  loadMeals();
}

function syncDateControls() {
  datePicker.value = state.selectedDate;
  selectedDateLabel.textContent = new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(`${state.selectedDate}T00:00:00`));
}

function setFeedback(message, isError = false) {
  feedbackMessage.textContent = message;
  feedbackMessage.classList.toggle("is-error", isError);
}

async function loadMeals() {
  state.loading = true;
  renderMeals();
  setFeedback("Loading meals...");

  try {
    const response = await fetch(`/api/meals?date=${state.selectedDate}`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Unable to load meals.");
    }

    state.meals = payload.meals || [];
    updateSummary(payload.summary);
    state.loading = false;
    renderMeals();

    if (state.meals.length === 0) {
      setFeedback("No meals planned for this day yet.");
    } else {
      setFeedback("Meals loaded.");
    }
  } catch (error) {
    state.meals = [];
    updateSummary();
    state.loading = false;
    renderMeals();
    setFeedback(error.message, true);
  }
}

function updateSummary(summary = null) {
  const total = summary?.totalMeals ?? state.meals.length;
  const completed =
    summary?.completedMeals ??
    state.meals.filter((meal) => meal.status === "Completed").length;

  totalMeals.textContent = total;
  completedMeals.textContent = completed;
}

function renderMeals() {
  mealGrid.innerHTML = "";

  if (state.loading) {
    mealGrid.innerHTML = '<div class="empty-state">Loading your meal plan...</div>';
    return;
  }

  if (state.meals.length === 0) {
    mealGrid.innerHTML =
      '<div class="empty-state">Nothing is scheduled for this date yet.</div>';
    return;
  }

  state.meals.forEach((meal) => {
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector(".meal-card");
    const badge = fragment.querySelector(".meal-card__badge");
    const title = fragment.querySelector(".meal-card__title");
    const description = fragment.querySelector(".meal-card__description");
    const meta = fragment.querySelector(".meal-card__meta");
    const checkbox = fragment.querySelector('input[type="checkbox"]');

    badge.textContent = meal.mealType;
    title.textContent = meal.description;
    description.textContent = meal.notes || "No extra notes for this meal.";
    checkbox.checked = meal.status === "Completed";

    if (checkbox.checked) {
      card.classList.add("is-completed");
    }

    [
      ["Status", meal.status],
      ["Calories", meal.calories ?? "Not set"],
      ["Date", meal.date || state.selectedDate],
    ].forEach(([label, value]) => {
      const wrapper = document.createElement("div");
      const dt = document.createElement("dt");
      const dd = document.createElement("dd");
      dt.textContent = label;
      dd.textContent = value;
      dd.style.margin = "0";
      wrapper.append(dt, dd);
      meta.appendChild(wrapper);
    });

    checkbox.addEventListener("change", () => toggleMealStatus(meal, checkbox, card));
    mealGrid.appendChild(fragment);
  });
}

async function toggleMealStatus(meal, checkbox, card) {
  const nextStatus = checkbox.checked ? "Completed" : "Pending";
  const previousStatus = meal.status;

  meal.status = nextStatus;
  card.classList.toggle("is-completed", checkbox.checked);
  updateSummary();
  setFeedback("Saving your update...");

  try {
    const response = await fetch("/api/meals/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: meal.id,
        date: meal.date || state.selectedDate,
        status: nextStatus,
      }),
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || "Unable to save the meal update.");
    }

    setFeedback("Meal status updated.");
    renderMeals();
  } catch (error) {
    meal.status = previousStatus;
    checkbox.checked = previousStatus === "Completed";
    card.classList.toggle("is-completed", checkbox.checked);
    updateSummary();
    setFeedback(error.message, true);
  }
}

syncDateControls();
loadMeals();

async function loadGroceries() {
  try {
    const res = await fetch("/api/groceries");
    const data = await res.json();

    const tbody = document.getElementById("groceriesTableBody");
    const totalEl = document.getElementById("totalCost");

    tbody.innerHTML = "";

    let totalCost = 0;

    data.groceries.forEach(item => {
      const row = document.createElement("tr");

      const itemTotal = Number(item.total) || (item.quantity * item.price);
      totalCost += itemTotal;

      row.innerHTML = `
        <td>
          <input type="checkbox" ${item.toBuy === "yes" ? "checked" : ""} 
            onchange="updateGrocery(${item.id}, this.checked, ${item.quantity}, ${item.price})">
        </td>
        <td>${item.name}</td>
        <td>${item.category || ""}</td>
        <td>
          <input type="number" value="${item.quantity}" min="1"
            onchange="updateGrocery(${item.id}, ${item.toBuy === "yes"}, this.value, ${item.price})">
        </td>
        <td>
          <input type="number" value="${item.price}" step="0.01"
            onchange="updateGrocery(${item.id}, ${item.toBuy === "yes"}, ${item.quantity}, this.value)">
        </td>
        <td>£${itemTotal.toFixed(2)}</td>
      `;

      tbody.appendChild(row);
    });

    totalEl.textContent = `£${totalCost.toFixed(2)}`;

  } catch (err) {
    console.error("Error loading groceries:", err);
  }
}
