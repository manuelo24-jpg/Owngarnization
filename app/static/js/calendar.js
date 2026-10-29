/**
 * Owngarnization — Integración de FullCalendar (Vistas Semana y Mes)
 */

const calendarManager = {
  calendarMonth: null,
  calendarWeek: null,

  init() {
    this.initMonthCalendar();
    this.initWeekCalendar();
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

  formatEvents(occurrences) {
    return occurrences.map(occ => {
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

      return {
        id: String(occ.id),
        title: `${statusIcon}${prefix}${task.title}`,
        start: start,
        end: end,
        allDay: !Boolean(occ.start_time),
        backgroundColor: colors.bg,
        borderColor: colors.border,
        textColor: colors.text,
        extendedProps: {
          occurrence: occ
        }
      };
    });
  },

  initMonthCalendar() {
    const el = document.getElementById("calendar-month");
    if (!el || !window.FullCalendar) return;

    this.calendarMonth = new FullCalendar.Calendar(el, {
      locale: "es",
      initialView: "dayGridMonth",
      headerToolbar: false, // Usamos nuestra propia barra de navegación superior
      height: "auto",
      editable: true,
      dayMaxEvents: 3,
      moreLinkContent: (args) => `+${args.num} más`,
      dateClick: (info) => {
        // Al hacer clic en un día en la vista mes, cambiar a vista Día para esa fecha
        if (window.appState) {
          window.appState.setDate(new Date(info.dateStr + "T00:00:00"));
          window.appState.switchView("day");
        }
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
  },

  updateWeekEvents(occurrences) {
    if (!this.calendarWeek) return;
    this.calendarWeek.removeAllEvents();
    this.calendarWeek.addEventSource(this.formatEvents(occurrences));
  },

  gotoDate(date) {
    if (this.calendarMonth) this.calendarMonth.gotoDate(date);
    if (this.calendarWeek) this.calendarWeek.gotoDate(date);
  }
};

window.calendarManager = calendarManager;
