/**
 * Owngarnization — Integración de FullCalendar (Vistas Semana y Mes)
 */

const calendarManager = {
  calendarMonth: null,
  calendarWeek: null,

  init() {
    this.ensureSkeletons();
    this.initMonthCalendar();
    this.initWeekCalendar();
  },

  getMonthSkeletonHtml() {
    const weekdays = Array(7).fill('<div class="skeleton-block cal-skel-weekday-pill"></div>').join("");
    let cells = "";
    for (let i = 0; i < 35; i++) {
      const hasEvent = (i % 3 === 0 || i % 5 === 1 || i % 7 === 2);
      cells += `
        <div class="cal-skel-day-cell">
          <div class="skeleton-block cal-skel-day-num"></div>
          ${hasEvent ? '<div class="skeleton-block cal-skel-day-event"></div>' : ""}
        </div>
      `;
    }
    return `
      <div class="cal-skel-weekdays">${weekdays}</div>
      <div class="cal-skel-month-grid">${cells}</div>
    `;
  },

  getWeekSkeletonHtml() {
    let rows = "";
    for (let i = 0; i < 7; i++) {
      const hasEvent = i % 2 === 0 || i % 3 === 0;
      rows += `
        <div class="cal-skel-week-row">
          <div class="cal-skel-week-row-header">
            <div class="skeleton-block cal-skel-week-dayname"></div>
            <div class="skeleton-block cal-skel-week-date"></div>
          </div>
          ${hasEvent ? '<div class="skeleton-block cal-skel-week-event"></div>' : ""}
        </div>
      `;
    }
    return `
      <div class="cal-skel-week-list">${rows}</div>
    `;
  },

  ensureSkeletons() {
    const monthEl = document.getElementById("calendar-month");
    if (monthEl && !monthEl.querySelector(".calendar-skeleton-overlay")) {
      const overlay = document.createElement("div");
      overlay.className = "calendar-skeleton-overlay";
      overlay.setAttribute("aria-hidden", "true");
      overlay.innerHTML = this.getMonthSkeletonHtml();
      monthEl.appendChild(overlay);
    }

    const weekEl = document.getElementById("calendar-week");
    if (weekEl && !weekEl.querySelector(".calendar-skeleton-overlay")) {
      const overlay = document.createElement("div");
      overlay.className = "calendar-skeleton-overlay";
      overlay.setAttribute("aria-hidden", "true");
      overlay.innerHTML = this.getWeekSkeletonHtml();
      weekEl.appendChild(overlay);
    }
  },

  setLoading(isLoading, which = null) {
    this.ensureSkeletons();
    if (!which || which === "month") {
      document.getElementById("calendar-month")?.classList.toggle("is-loading", Boolean(isLoading));
    }
    if (!which || which === "week") {
      document.getElementById("calendar-week")?.classList.toggle("is-loading", Boolean(isLoading));
    }
  },

  getImportanceColors(importance) {
    switch (importance) {
      case "low":
        return { bg: "#EFE9E0", border: "#D8CFBE", text: "#111111" };
      case "high":
        return { bg: "#C9A57C", border: "#B58F63", text: "#111111" };
      case "urgent":
        return { bg: "#111111", border: "#000000", text: "#FFFFFF" };
      case "medium":
      default:
        return { bg: "#E3CFB4", border: "#CDB697", text: "#111111" };
    }
  },

  getImportanceWeight(importance) {
    switch (importance) {
      case "urgent":
        return 1;
      case "high":
        return 2;
      case "medium":
        return 3;
      case "low":
      default:
        return 4;
    }
  },

  /**
   * Agrupa las ocurrencias por fecha y selecciona únicamente la tarea principal
   * de cada día para evitar sobrecargar las vistas de Semana y Mes.
   */
  selectSinglePerDay(occurrences) {
    const byDate = new Map();
    for (const occ of occurrences) {
      if (!byDate.has(occ.date)) {
        byDate.set(occ.date, []);
      }
      byDate.get(occ.date).push(occ);
    }

    const result = [];
    for (const [, dayOccs] of byDate.entries()) {
      const sorted = [...dayOccs].sort((a, b) => {
        const aDone = a.status === "done" ? 1 : 0;
        const bDone = b.status === "done" ? 1 : 0;
        if (aDone !== bDone) return aDone - bDone;

        const aKind = a.task.kind === "daily" ? 0 : 1;
        const bKind = b.task.kind === "daily" ? 0 : 1;
        if (aKind !== bKind) return aKind - bKind;

        const aImp = this.getImportanceWeight(a.task.importance);
        const bImp = this.getImportanceWeight(b.task.importance);
        if (aImp !== bImp) return aImp - bImp;

        const aTime = a.start_time || a.task.start_time || "99:99:99";
        const bTime = b.start_time || b.task.start_time || "99:99:99";
        return aTime.localeCompare(bTime);
      });

      result.push({
        occ: sorted[0],
        extraCount: sorted.length - 1,
        totalCount: sorted.length
      });
    }

    return result;
  },

  formatEvents(occurrences) {
    const singlePerDay = this.selectSinglePerDay(occurrences);

    return singlePerDay.map(({ occ, extraCount, totalCount }) => {
      const task = occ.task;
      const colors = this.getImportanceColors(task.importance);

      let start = occ.date;
      if (occ.start_time) {
        start = `${occ.date}T${occ.start_time}`;
      }

      let end = occ.date;
      if (occ.end_time) {
        end = `${occ.date}T${occ.end_time}`;
      }

      const prefix = task.kind === "common" ? "🔁 " : "";
      const statusIcon = occ.status === "done" ? "✓ " : occ.status === "in_progress" ? "◐ " : "";
      const extraSuffix = extraCount > 0 ? ` (+${extraCount})` : "";

      return {
        id: String(occ.id),
        title: `${statusIcon}${prefix}${task.title}${extraSuffix}`,
        start: start,
        end: end,
        allDay: !Boolean(occ.start_time),
        backgroundColor: colors.bg,
        borderColor: colors.border,
        textColor: colors.text,
        extendedProps: {
          occurrence: occ,
          extraCount: extraCount,
          totalCount: totalCount
        }
      };
    });
  },

  openDayFromCalendar(dateStrOrObj) {
    if (!window.appState) return;
    const targetDate =
      typeof dateStrOrObj === "string"
        ? new Date(dateStrOrObj.split("T")[0] + "T00:00:00")
        : new Date(dateStrOrObj);
    window.appState.setDate(targetDate);
    window.appState.switchView("day");
  },

  initMonthCalendar() {
    const el = document.getElementById("calendar-month");
    if (!el || !window.FullCalendar) return;

    this.calendarMonth = new FullCalendar.Calendar(el, {
      locale: "es",
      initialView: "dayGridMonth",
      headerToolbar: false,
      height: "auto",
      editable: true,
      dayMaxEvents: false,
      navLinks: true,
      navLinkDayClick: (date) => {
        this.openDayFromCalendar(date);
      },
      dateClick: (info) => {
        this.openDayFromCalendar(info.dateStr);
      },
      eventClick: (info) => {
        info.jsEvent.preventDefault();
        const occ = info.event.extendedProps.occurrence;
        if (occ && window.modal) {
          window.modal.openDetailDrawer(occ);
        }
      },
      eventDrop: async (info) => {
        const occ = info.event.extendedProps.occurrence;
        const newDateStr = info.event.startStr.split("T")[0];

        try {
          await api.patch(`/api/occurrences/${occ.id}`, { date: newDateStr });
          showToast(`Tarea movida al ${newDateStr}`, "success");
          occ.date = newDateStr;
        } catch (err) {
          info.revert();
          showToast(err.message || "No se pudo mover la tarea", "error");
        }
      }
    });

    this.calendarMonth.render();
  },

  initWeekCalendar() {
    const el = document.getElementById("calendar-week");
    if (!el || !window.FullCalendar) return;

    const isMobileVersion = Boolean(document.querySelector('[data-app-mode="mobile"]'));

    this.calendarWeek = new FullCalendar.Calendar(el, {
      locale: "es",
      initialView: isMobileVersion ? "listWeek" : "dayGridWeek",
      headerToolbar: false,
      height: "auto",
      editable: true,
      dayMaxEvents: false,
      navLinks: true,
      navLinkDayClick: (date) => {
        this.openDayFromCalendar(date);
      },
      noEventsText: "No hay tareas programadas en esta semana",
      eventClick: (info) => {
        info.jsEvent.preventDefault();
        const occ = info.event.extendedProps.occurrence;
        if (occ && window.modal) {
          window.modal.openDetailDrawer(occ);
        }
      },
      eventDrop: async (info) => {
        const occ = info.event.extendedProps.occurrence;
        const newDateStr = info.event.startStr.split("T")[0];

        try {
          await api.patch(`/api/occurrences/${occ.id}`, { date: newDateStr });
          showToast(`Tarea movida al ${newDateStr}`, "success");
          occ.date = newDateStr;
        } catch (err) {
          info.revert();
          showToast(err.message || "No se pudo mover la tarea", "error");
        }
      }
    });

    this.calendarWeek.render();
  },

  updateMonthEvents(occurrences) {
    if (!this.calendarMonth) return;
    this.calendarMonth.removeAllEvents();
    this.calendarMonth.addEventSource(this.formatEvents(occurrences));
    this.setLoading(false, "month");
    setTimeout(() => this.calendarMonth?.updateSize(), 50);
  },

  updateWeekEvents(occurrences) {
    if (!this.calendarWeek) return;
    this.calendarWeek.removeAllEvents();
    this.calendarWeek.addEventSource(this.formatEvents(occurrences));
    this.setLoading(false, "week");
    setTimeout(() => this.calendarWeek?.updateSize(), 50);
  },

  gotoDate(date) {
    if (this.calendarMonth) this.calendarMonth.gotoDate(date);
    if (this.calendarWeek) this.calendarWeek.gotoDate(date);
  }
};

window.calendarManager = calendarManager;
