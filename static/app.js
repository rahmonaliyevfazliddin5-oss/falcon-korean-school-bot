// Falcon Kibertexnology School - Telegram Mini App Frontend Logic
(function () {
  "use strict";

  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  // State
  let currentUser = null;
  let isAdmin = false;
  let allStudents = [];
  let attendanceState = {}; // studentId -> 1 (present) or 0 (absent)
  let gradesState = {}; // studentId -> { score, comment, has_fine }
  let activeTab = "attendance";

  // Sana boshqaruvi
  // Dushanba=1 ... Shanba=6, Yakshanba=0 (JS Date.getDay())
  let currentMonday = getMonday(new Date());
  let activeDate = formatDateISO(getInitialDate());

  // DOM elementlar
  const parentView = document.getElementById("parent-view");
  const adminView = document.getElementById("admin-view");
  const dateBar = document.getElementById("date-bar");
  const currentDateLabel = document.getElementById("current-date-label");
  const dayTabsContainer = document.getElementById("day-tabs-container");
  const prevWeekBtn = document.getElementById("prev-week-btn");
  const nextWeekBtn = document.getElementById("next-week-btn");

  const attendanceList = document.getElementById("attendance-list");
  const saveAttendanceBtn = document.getElementById("save-attendance-btn");

  const gradesList = document.getElementById("grades-list");

  const studentsList = document.getElementById("students-list");
  const studentSearchInput = document.getElementById("student-search-input");
  const openAddStudentBtn = document.getElementById("open-add-student-btn");
  const addStudentModal = document.getElementById("add-student-modal");
  const newStudentNameInput = document.getElementById("new-student-name");
  const cancelAddStudentBtn = document.getElementById("cancel-add-student-btn");
  const confirmAddStudentBtn = document.getElementById("confirm-add-student-btn");

  const editStudentModal = document.getElementById("edit-student-modal");
  const editStudentNameInput = document.getElementById("edit-student-name");
  const editStudentIdInput = document.getElementById("edit-student-id");
  const cancelEditStudentBtn = document.getElementById("cancel-edit-student-btn");
  const confirmEditStudentBtn = document.getElementById("confirm-edit-student-btn");

  const debtsList = document.getElementById("debts-list");
  const debtSearchInput = document.getElementById("debt-search-input");
  const paymentModal = document.getElementById("payment-modal");
  const paymentModalTitle = document.getElementById("payment-modal-title");
  const paymentModalDebt = document.getElementById("payment-modal-debt");
  const paymentAmountInput = document.getElementById("payment-amount-input");
  const paymentStudentIdInput = document.getElementById("payment-student-id");
  const cancelPaymentBtn = document.getElementById("cancel-payment-btn");
  const confirmPaymentBtn = document.getElementById("confirm-payment-btn");

  const historyModal = document.getElementById("history-modal");
  const historyModalTitle = document.getElementById("history-modal-title");
  const historyPaymentsList = document.getElementById("history-payments-list");
  const undoLastPaymentBtn = document.getElementById("undo-last-payment-btn");
  const closeHistoryBtn = document.getElementById("close-history-btn");

  // Haptic Feedback yordamchisi
  function haptic(type = "light") {
    try {
      if (tg?.HapticFeedback) {
        if (type === "success" || type === "error" || type === "warning") {
          tg.HapticFeedback.notificationOccurred(type);
        } else if (type === "selection") {
          tg.HapticFeedback.selectionChanged();
        } else {
          tg.HapticFeedback.impactOccurred(type);
        }
      }
    } catch (_) {}
  }

  // Toast xabarnoma ko'rsatish
  function showToast(message) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 2500);
  }

  // Pul formatlash: 10000 -> "10 000 so'm"
  function formatMoney(amount) {
    const num = Math.round(Number(amount) || 0);
    return num.toLocaleString("ru-RU").replace(/,/g, " ") + " so'm";
  }

  // Sana formatlash yordamchilari
  const UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];
  const UZ_DAYS = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
  const SHORT_DAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh"]; // Dushanba dan Shanba gacha

  function getMonday(d) {
    const date = new Date(d);
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(date.setDate(diff));
  }

  function getInitialDate() {
    const now = new Date();
    // Agar bugun yakshanba bo'lsa, dushanbaga yoki shanbaga o'tkazamiz
    if (now.getDay() === 0) {
      now.setDate(now.getDate() - 1);
    }
    return now;
  }

  function formatDateISO(d) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function formatDateNice(isoStr) {
    const [y, m, d] = isoStr.split("-").map(Number);
    const dateObj = new Date(y, m - 1, d);
    const dayName = UZ_DAYS[dateObj.getDay()];
    const monthName = UZ_MONTHS[m - 1];
    return `${d}-${monthName} ${y}, ${dayName}`;
  }

  // API so'rov yuborish
  async function apiFetch(endpoint, options = {}) {
    const initData = tg?.initData || "";
    const headers = {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": initData,
      ...(options.headers || {})
    };

    const res = await fetch(endpoint, { ...options, headers });
    if (res.status === 401 || res.status === 403) {
      // Ruxsat yo'q
      showParentView();
      throw new Error("Ruxsat yo'q");
    }
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Xatolik yuz berdi");
    }
    return data;
  }

  // ==================== INITIALIZATION ====================
  async function initApp() {
    try {
      const meData = await apiFetch("/api/me");
      if (!meData.authenticated || !meData.is_admin) {
        showParentView();
        return;
      }

      currentUser = meData.user;
      isAdmin = true;
      showAdminView();
      renderDayTabs();
      await loadStudents();
      await loadTabData();
    } catch (err) {
      showParentView();
    }
  }

  function showParentView() {
    parentView.style.display = "flex";
    adminView.style.display = "none";
  }

  function showAdminView() {
    parentView.style.display = "none";
    adminView.style.display = "block";
  }

  // ==================== DATE SELECTION ====================
  function renderDayTabs() {
    dayTabsContainer.innerHTML = "";
    currentDateLabel.textContent = formatDateNice(activeDate);

    // Dushanbadan Shanbagacha 6 kun
    for (let i = 0; i < 6; i++) {
      const dayDate = new Date(currentMonday);
      dayDate.setDate(currentMonday.getDate() + i);
      const iso = formatDateISO(dayDate);
      const isActive = iso === activeDate;

      const tab = document.createElement("div");
      tab.className = `day-tab ${isActive ? "active" : ""}`;
      tab.innerHTML = `
        <span class="day-name">${SHORT_DAYS[i]}</span>
        <span class="day-num">${dayDate.getDate()}</span>
      `;

      tab.addEventListener("click", () => {
        haptic("light");
        activeDate = iso;
        renderDayTabs();
        loadTabData();
      });

      dayTabsContainer.appendChild(tab);
    }
  }

  prevWeekBtn.addEventListener("click", () => {
    haptic("light");
    currentMonday.setDate(currentMonday.getDate() - 7);
    activeDate = formatDateISO(currentMonday);
    renderDayTabs();
    loadTabData();
  });

  nextWeekBtn.addEventListener("click", () => {
    haptic("light");
    currentMonday.setDate(currentMonday.getDate() + 7);
    activeDate = formatDateISO(currentMonday);
    renderDayTabs();
    loadTabData();
  });

  // ==================== NAVIGATION TABS ====================
  const navButtons = document.querySelectorAll(".nav-item");
  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabName = btn.getAttribute("data-tab");
      if (tabName === activeTab) return;

      haptic("selection");
      activeTab = tabName;

      navButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".tab-content").forEach((tc) => tc.classList.remove("active"));
      document.getElementById(`tab-${tabName}`).classList.add("active");

      // Sana paneli faqat Davomat va Baho bo'limlarida ko'rinadi
      if (tabName === "attendance" || tabName === "grades") {
        dateBar.style.display = "block";
      } else {
        dateBar.style.display = "none";
      }

      loadTabData();
    });
  });

  async function loadTabData() {
    if (activeTab === "attendance") {
      await loadAttendance();
    } else if (activeTab === "grades") {
      await loadGrades();
    } else if (activeTab === "students") {
      renderStudentsList();
    } else if (activeTab === "debts") {
      await loadDebts();
    }
  }

  // ==================== 1. STUDENTS ====================
  async function loadStudents() {
    try {
      const data = await apiFetch("/api/students?active_only=true");
      allStudents = data.students || [];
    } catch (err) {
      showToast("O'quvchilarni yuklashda xatolik");
    }
  }

  function renderStudentsList() {
    const search = studentSearchInput.value.toLowerCase().trim();
    studentsList.innerHTML = "";

    const filtered = allStudents.filter((s) =>
      s.full_name.toLowerCase().includes(search)
    );

    if (filtered.length === 0) {
      studentsList.innerHTML = `<div style="text-align: center; color: var(--hint-color); padding: 30px;">O'quvchilar topilmadi</div>`;
      return;
    }

    filtered.forEach((s) => {
      const card = document.createElement("div");
      card.className = "student-card";
      card.innerHTML = `
        <div class="student-info">
          <span class="student-name">${s.full_name}</span>
          <span class="student-sub">${s.group_name || "Guruhsiz"}</span>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="action-btn-small history edit-btn" data-id="${s.id}" data-name="${s.full_name}" aria-label="Tahrirlash">
            ✏️
          </button>
          <button class="action-btn-small history delete-btn" data-id="${s.id}" data-name="${s.full_name}" aria-label="O'chirish" style="color: var(--danger-color);">
            🗑️
          </button>
        </div>
      `;

      card.querySelector(".edit-btn").addEventListener("click", () => {
        haptic("light");
        editStudentIdInput.value = s.id;
        editStudentNameInput.value = s.full_name;
        editStudentModal.style.display = "flex";
      });

      card.querySelector(".delete-btn").addEventListener("click", async () => {
        haptic("warning");
        const confirmMsg = `${s.full_name} ni arxivga o'tkazishni tasdiqlaysizmi?`;
        if (confirm(confirmMsg)) {
          try {
            await apiFetch(`/api/students/${s.id}`, { method: "DELETE" });
            haptic("success");
            showToast("O'quvchi arxivlandi");
            await loadStudents();
            renderStudentsList();
          } catch (e) {
            showToast(e.message);
          }
        }
      });

      studentsList.appendChild(card);
    });
  }

  studentSearchInput.addEventListener("input", renderStudentsList);

  // Yangi o'quvchi qo'shish modal boshqaruvi
  openAddStudentBtn.addEventListener("click", () => {
    haptic("light");
    newStudentNameInput.value = "";
    addStudentModal.style.display = "flex";
    newStudentNameInput.focus();
  });

  cancelAddStudentBtn.addEventListener("click", () => {
    addStudentModal.style.display = "none";
  });

  confirmAddStudentBtn.addEventListener("click", async () => {
    const name = newStudentNameInput.value.trim();
    if (!name || name.length < 2) {
      showToast("Ism-familiyani to'liq kiriting");
      return;
    }

    try {
      await apiFetch("/api/students", {
        method: "POST",
        body: JSON.stringify({ full_name: name })
      });
      haptic("success");
      showToast("O'quvchi muvaffaqiyatli qo'shildi");
      addStudentModal.style.display = "none";
      await loadStudents();
      renderStudentsList();
    } catch (e) {
      showToast(e.message);
    }
  });

  // Tahrirlash modal boshqaruvi
  cancelEditStudentBtn.addEventListener("click", () => {
    editStudentModal.style.display = "none";
  });

  confirmEditStudentBtn.addEventListener("click", async () => {
    const id = editStudentIdInput.value;
    const name = editStudentNameInput.value.trim();
    if (!name || name.length < 2) {
      showToast("Ism-familiyani to'liq kiriting");
      return;
    }

    try {
      await apiFetch(`/api/students/${id}`, {
        method: "PUT",
        body: JSON.stringify({ full_name: name })
      });
      haptic("success");
      showToast("Ma'lumotlar saqlandi");
      editStudentModal.style.display = "none";
      await loadStudents();
      renderStudentsList();
    } catch (e) {
      showToast(e.message);
    }
  });

  // ==================== 2. ATTENDANCE (DAVOMAT) ====================
  async function loadAttendance() {
    attendanceList.innerHTML = `<div class="card-list"><div class="student-card skeleton" style="height: 60px;"></div><div class="student-card skeleton" style="height: 60px;"></div></div>`;
    try {
      const data = await apiFetch(`/api/attendance?date=${activeDate}`);
      attendanceState = data.attendance || {};
      renderAttendanceList();
    } catch (err) {
      showToast(err.message);
    }
  }

  function renderAttendanceList() {
    attendanceList.innerHTML = "";

    allStudents.forEach((s) => {
      // Standart: 1 (Keldi)
      const isPresent = attendanceState[s.id] !== undefined ? attendanceState[s.id] === 1 : true;
      attendanceState[s.id] = isPresent ? 1 : 0;

      const card = document.createElement("div");
      card.className = "student-card";
      card.innerHTML = `
        <div class="student-info">
          <span class="student-name">${s.full_name}</span>
          <span class="student-sub">${s.group_name || "Guruhsiz"}</span>
        </div>
        <button class="attendance-toggle-btn ${isPresent ? "present" : "absent"}" data-id="${s.id}">
          <span>${isPresent ? "✅ Keldi" : "❌ Kelmadi"}</span>
        </button>
      `;

      const toggleBtn = card.querySelector(".attendance-toggle-btn");
      toggleBtn.addEventListener("click", () => {
        haptic("selection");
        const newStatus = attendanceState[s.id] === 1 ? 0 : 1;
        attendanceState[s.id] = newStatus;

        if (newStatus === 1) {
          toggleBtn.className = "attendance-toggle-btn present";
          toggleBtn.innerHTML = "<span>✅ Keldi</span>";
        } else {
          toggleBtn.className = "attendance-toggle-btn absent";
          toggleBtn.innerHTML = "<span>❌ Kelmadi</span>";
        }
      });

      attendanceList.appendChild(card);
    });
  }

  saveAttendanceBtn.addEventListener("click", async () => {
    haptic("light");
    saveAttendanceBtn.disabled = true;
    saveAttendanceBtn.textContent = "Saqlanmoqda...";

    const items = Object.keys(attendanceState).map((id) => ({
      student_id: Number(id),
      present: attendanceState[id]
    }));

    try {
      const res = await apiFetch("/api/attendance", {
        method: "POST",
        body: JSON.stringify({
          date: activeDate,
          items: items,
          send_broadcast: true
        })
      });
      haptic("success");
      showToast(res.message || "Davomat saqlandi va yuborilmoqda");
    } catch (e) {
      haptic("error");
      showToast(e.message);
    } finally {
      saveAttendanceBtn.disabled = false;
      saveAttendanceBtn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
        Saqlash va yuborish
      `;
    }
  });

  // ==================== 3. GRADES (BAHOLAR & JARIMA) ====================
  async function loadGrades() {
    gradesList.innerHTML = `<div class="card-list"><div class="grade-card skeleton" style="height: 120px;"></div><div class="grade-card skeleton" style="height: 120px;"></div></div>`;
    try {
      const data = await apiFetch(`/api/grades?date=${activeDate}`);
      gradesState = data.grades || {};
      renderGradesList();
    } catch (err) {
      showToast(err.message);
    }
  }

  function renderGradesList() {
    gradesList.innerHTML = "";

    allStudents.forEach((s) => {
      const g = gradesState[s.id] || { score: 0, comment: "", has_fine: false };
      const card = document.createElement("div");
      card.className = "grade-card";

      let scoreBtnsHtml = "";
      for (let sc = 0; sc <= 10; sc++) {
        const isSel = g.score === sc;
        scoreBtnsHtml += `<button class="score-btn ${isSel ? "selected" : ""}" data-score="${sc}">${sc}</button>`;
      }

      card.innerHTML = `
        <div class="grade-card-top">
          <div class="student-info">
            <span class="student-name">${s.full_name}</span>
            <span class="student-sub">${s.group_name || "Guruhsiz"}</span>
          </div>
          <span class="grade-score-badge">${g.score} ball</span>
        </div>

        <div class="score-picker">
          ${scoreBtnsHtml}
        </div>

        <button class="no-homework-btn ${g.has_fine ? "active" : ""}">
          <span>⚠️ Vazifa qilmadi (+10 000 so'm jarima)</span>
        </button>

        <input type="text" class="grade-comment-input" placeholder="Izoh (ixtiyoriy)..." value="${g.comment || ""}">
      `;

      const scoreBadge = card.querySelector(".grade-score-badge");
      const noHwBtn = card.querySelector(".no-homework-btn");
      const commentInput = card.querySelector(".grade-comment-input");
      const scoreBtns = card.querySelectorAll(".score-btn");

      // Ball tanlash
      scoreBtns.forEach((b) => {
        b.addEventListener("click", async () => {
          haptic("light");
          const sc = Number(b.getAttribute("data-score"));
          scoreBtns.forEach((x) => x.classList.remove("selected"));
          b.classList.add("selected");
          scoreBadge.textContent = `${sc} ball`;

          // Agar vazifa qilmadi faol bo'lsa, o'chiramiz
          if (noHwBtn.classList.contains("active")) {
            noHwBtn.classList.remove("active");
          }

          await saveStudentGrade(s.id, sc, commentInput.value, false);
        });
      });

      // 'Vazifa qilmadi' tugmasi
      noHwBtn.addEventListener("click", async () => {
        haptic("warning");
        const isActive = noHwBtn.classList.contains("active");
        const newActive = !isActive;

        if (newActive) {
          noHwBtn.classList.add("active");
          scoreBadge.textContent = "0 ball";
          scoreBtns.forEach((x) => x.classList.remove("selected"));
          const zeroBtn = card.querySelector('.score-btn[data-score="0"]');
          if (zeroBtn) zeroBtn.classList.add("selected");
          await saveStudentGrade(s.id, 0, commentInput.value, true);
          showToast(`${s.full_name}: +10 000 so'm jarima qo'shildi`);
        } else {
          noHwBtn.classList.remove("active");
          await saveStudentGrade(s.id, 0, commentInput.value, false);
          showToast(`${s.full_name}: Jarima bekor qilindi`);
        }
      });

      // Izoh o'zgarishi
      commentInput.addEventListener("change", async () => {
        const currentScore = Number(scoreBadge.textContent.split(" ")[0]) || 0;
        const hasFine = noHwBtn.classList.contains("active");
        await saveStudentGrade(s.id, currentScore, commentInput.value, hasFine);
      });

      gradesList.appendChild(card);
    });
  }

  async function saveStudentGrade(studentId, score, comment, noHomework) {
    try {
      await apiFetch("/api/grades", {
        method: "POST",
        body: JSON.stringify({
          student_id: studentId,
          date: activeDate,
          score: score,
          comment: comment,
          no_homework: noHomework
        })
      });
      gradesState[studentId] = {
        score: score,
        comment: comment,
        has_fine: noHomework
      };
    } catch (err) {
      showToast(err.message);
    }
  }

  // ==================== 4. DEBTS & PAYMENTS (QARZ) ====================
  let debtsData = [];

  async function loadDebts() {
    debtsList.innerHTML = `<div class="card-list"><div class="student-card skeleton" style="height: 70px;"></div><div class="student-card skeleton" style="height: 70px;"></div></div>`;
    try {
      const data = await apiFetch("/api/debts");
      debtsData = data.debts || [];
      renderDebtsList();
    } catch (err) {
      showToast(err.message);
    }
  }

  function renderDebtsList() {
    const search = debtSearchInput.value.toLowerCase().trim();
    debtsList.innerHTML = "";

    const filtered = debtsData.filter((d) =>
      d.full_name.toLowerCase().includes(search)
    );

    if (filtered.length === 0) {
      debtsList.innerHTML = `<div style="text-align: center; color: var(--hint-color); padding: 30px;">Qarzdorlar topilmadi</div>`;
      return;
    }

    filtered.forEach((d) => {
      const card = document.createElement("div");
      card.className = "student-card";
      card.innerHTML = `
        <div class="student-info">
          <span class="student-name">${d.full_name}</span>
          <span class="student-sub">Jami jarima: ${formatMoney(d.total_fines)} | To'landi: ${formatMoney(d.total_payments)}</span>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
          <span class="debt-amount-badge ${d.debt > 0 ? "has-debt" : ""}">${formatMoney(d.debt)}</span>
          <div class="debt-actions">
            ${
              d.debt > 0
                ? `<button class="action-btn-small pay pay-btn" data-id="${d.student_id}" data-name="${d.full_name}" data-debt="${d.debt}">To'lov</button>`
                : ""
            }
            <button class="action-btn-small history history-btn" data-id="${d.student_id}" data-name="${d.full_name}">Tarix</button>
          </div>
        </div>
      `;

      // To'lov qabul qilish
      const payBtn = card.querySelector(".pay-btn");
      if (payBtn) {
        payBtn.addEventListener("click", () => {
          haptic("light");
          paymentStudentIdInput.value = d.student_id;
          paymentModalTitle.textContent = `${d.full_name} — To'lov`;
          paymentModalDebt.textContent = `Joriy qarz: ${formatMoney(d.debt)}`;
          paymentAmountInput.value = "";
          paymentAmountInput.max = d.debt;
          paymentModal.style.display = "flex";
          paymentAmountInput.focus();
        });
      }

      // To'lovlar tarixi
      card.querySelector(".history-btn").addEventListener("click", () => {
        haptic("light");
        openHistoryModal(d.student_id, d.full_name);
      });

      debtsList.appendChild(card);
    });
  }

  debtSearchInput.addEventListener("input", renderDebtsList);

  // To'lov modal boshqaruvi
  cancelPaymentBtn.addEventListener("click", () => {
    paymentModal.style.display = "none";
  });

  confirmPaymentBtn.addEventListener("click", async () => {
    const studentId = paymentStudentIdInput.value;
    const amount = Number(paymentAmountInput.value);

    if (!amount || amount <= 0) {
      showToast("To'g'ri to'lov summasini kiriting");
      return;
    }

    try {
      const res = await apiFetch("/api/payments", {
        method: "POST",
        body: JSON.stringify({
          student_id: studentId,
          amount: amount
        })
      });
      haptic("success");
      showToast(res.message || "To'lov muvaffaqiyatli qabul qilindi");
      paymentModal.style.display = "none";
      await loadDebts();
    } catch (e) {
      haptic("error");
      showToast(e.message);
    }
  });

  // Tarix modal boshqaruvi
  async function openHistoryModal(studentId, studentName) {
    historyModalTitle.textContent = `${studentName} — To'lovlar`;
    historyPaymentsList.innerHTML = "Yuklanmoqda...";
    undoLastPaymentBtn.style.display = "none";
    historyModal.style.display = "flex";

    try {
      const data = await apiFetch(`/api/payments/${studentId}`);
      const payments = data.payments || [];

      if (payments.length === 0) {
        historyPaymentsList.innerHTML = `<div style="text-align: center; color: var(--hint-color); padding: 15px;">To'lovlar mavjud emas</div>`;
        return;
      }

      historyPaymentsList.innerHTML = "";
      payments.forEach((p, idx) => {
        const item = document.createElement("div");
        item.style.cssText = "display: flex; justify-content: space-between; padding: 8px 12px; background: var(--secondary-bg); border-radius: 8px;";
        item.innerHTML = `
          <span style="font-size: 13px; color: var(--hint-color);">${p.created_at || "Yaqinda"}</span>
          <span style="font-size: 14px; font-weight: 600; color: var(--success-color);">+${formatMoney(p.amount)}</span>
        `;
        historyPaymentsList.appendChild(item);
      });

      // Oxirgi to'lovni bekor qilish tugmasi
      undoLastPaymentBtn.style.display = "block";
      undoLastPaymentBtn.onclick = async () => {
        haptic("warning");
        if (confirm("Oxirgi to'lovni bekor qilishni tasdiqlaysizmi?")) {
          try {
            await apiFetch(`/api/payments/${studentId}/last`, { method: "DELETE" });
            haptic("success");
            showToast("Oxirgi to'lov bekor qilindi");
            historyModal.style.display = "none";
            await loadDebts();
          } catch (e) {
            showToast(e.message);
          }
        }
      };
    } catch (err) {
      historyPaymentsList.innerHTML = `<div style="color: var(--danger-color);">${err.message}</div>`;
    }
  }

  closeHistoryBtn.addEventListener("click", () => {
    historyModal.style.display = "none";
  });

  // Ilovani ishga tushirish
  document.addEventListener("DOMContentLoaded", initApp);
})();
