// -------------------------
// helper
// -------------------------
async function postJSON(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

// -------------------------
// indicator coloring (main cards)
// -------------------------
function colorIndicator(el, level) {
  if (!el) return;

  el.classList.remove("status-low", "status-medium", "status-high");

  if (level === "Low") el.classList.add("status-low");
  else if (level === "Medium") el.classList.add("status-medium");
  else if (level === "High") el.classList.add("status-high");
}

// -------------------------
// modal
// -------------------------
function showModal(data) {
  const modal = document.getElementById("modal");
  if (!modal) return;

  document.getElementById("modalTitle").textContent = data.location;
  document.getElementById("modalLevel").textContent = data.level;
  document.getElementById("modalPeople").textContent = data.average_people;
  document.getElementById("modalCapacity").textContent = data.capacity;
  document.getElementById("modalPercent").textContent = data.percent;

  modal.classList.remove("hidden");

  const directionsBtn = document.getElementById("directionsBtn");
  if (directionsBtn) {
    directionsBtn.onclick = () => {
      const url =
        "https://www.google.com/maps/dir/?api=1&destination=" +
        encodeURIComponent(data.location);
      window.open(url, "_blank");
    };
  }
}

function hideModal() {
  const modal = document.getElementById("modal");
  if (modal) modal.classList.add("hidden");
}

// -------------------------
// update sub-location card
// -------------------------
function updateSubLocationUI(data) {
  const id = data.id;

  const peopleEl = document.getElementById(`people-${id}`);
  const levelEl = document.getElementById(`level-${id}`);
  const percentEl = document.getElementById(`percent-${id}`);
  const barEl = document.getElementById(`bar-${id}`);
  const timeEl = document.getElementById(`time-${id}`);

  if (peopleEl) peopleEl.textContent = data.average_people;
  if (percentEl) percentEl.textContent = data.percent;
  if (timeEl) timeEl.textContent = new Date().toLocaleString();

  if (levelEl) {
    levelEl.textContent = data.level;
    levelEl.className =
      data.level === "High"
        ? "text-red-600 font-semibold"
        : data.level === "Medium"
        ? "text-yellow-600 font-semibold"
        : "text-green-600 font-semibold";
  }

  if (barEl) {
    barEl.style.width = data.percent + "%";
    barEl.className =
      "h-3 rounded transition-all duration-700 " +
      (data.level === "High"
        ? "bg-red-500"
        : data.level === "Medium"
        ? "bg-yellow-400"
        : "bg-green-500");
  }
}

// -------------------------
// DOM READY
// -------------------------
document.addEventListener("DOMContentLoaded", () => {
  // hover effect
  document.querySelectorAll(".space-card").forEach((card) => {
    card.addEventListener("mouseenter", () =>
      card.classList.add("ring-2", "ring-teal-400")
    );
    card.addEventListener("mouseleave", () =>
      card.classList.remove("ring-2", "ring-teal-400")
    );
  });

  // -------------------------
  // CHECK (YOLO)
  // -------------------------
  document.querySelectorAll(".check-btn").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      const locId = ev.currentTarget.dataset.loc;
      const indicator = document.getElementById("indicator-" + locId);

      btn.disabled = true;
      btn.textContent = "Analyzing...";

      try {
        const json = await postJSON("/api/analyze", { location: locId });

        if (json.error) {
          alert(json.error);
        } else {
          colorIndicator(indicator, json.level);
          updateSubLocationUI(json); // 🔥 NEW
          showModal(json);
          btn.textContent = "Check Again";
        }
      } catch (err) {
        alert("Request failed");
        btn.textContent = "Check";
      } finally {
        btn.disabled = false;
      }
    });
  });

  // -------------------------
  // PREVIOUS (DB)
  // -------------------------
  document.querySelectorAll(".prev-btn").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      const locId = ev.currentTarget.dataset.loc;
      const indicator = document.getElementById("indicator-" + locId);

      try {
        const json = await postJSON("/api/get_last_status", {
          location: locId,
        });

        if (json.error) {
          alert(json.error);
        } else {
          colorIndicator(indicator, json.level);
          updateSubLocationUI(json); // 🔥 NEW
          showModal(json);
        }
      } catch (err) {
        alert("Failed to load previous data");
      }
    });
  });

  // -------------------------
  // modal handlers
  // -------------------------
  const modalClose = document.getElementById("modalClose");
  if (modalClose) modalClose.addEventListener("click", hideModal);

  const modal = document.getElementById("modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) hideModal();
    });
  }
});
