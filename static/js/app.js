/**
 * Hitachi Project Tracker - Offline Single Page Application (SPA)
 * Vanilla JavaScript Command Center Controller
 */

// Global State
const state = {
  projects: [],
  filteredProjects: [],
  activeProjectId: null,
  activeProjectData: null,
  activeTab: 'overview',
  collapsedPhases: new Set(), // Set of phase IDs that are collapsed
  shiftSummaryData: null,
  shiftSelectedProjectIds: new Set(),
  users: [],
  activeUserId: null,
};

// SVG Heroicons Library (Embedded Inline to avoid external CDNs)
const ICONS = {
  chevronDown: `<svg class="w-4 h-4 transition-transform duration-200" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5"></path></svg>`,
  chevronRight: `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"></path></svg>`,
  plusMuted: `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"></path></svg>`,
  trash: `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"></path></svg>`,
  pencil: `<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"></path></svg>`,
  plus: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"></path></svg>`,
  check: `<svg class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"></path></svg>`,
  paperclip: `<svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.37l-9.878 9.88a1.5 1.5 0 01-2.122-2.123l8.818-8.818"></path></svg>`,
  arrowTopRightOnSquare: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"></path></svg>`,
  arrowDownTray: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"></path></svg>`,
  spinner: `<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>`,
  clock: `<svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
};

// ---------------------------------------------------------------------------
// DESIGN TOKENS (UI-only)
// NOTE: Tailwind is compiled ahead of time and only sees *complete literal*
// class strings in this file. Never build class names dynamically.
// ---------------------------------------------------------------------------
const STATUS_STYLES = {
  Active: {
    dot: 'bg-emerald-500 ring-4 ring-emerald-500/15 shadow-[0_0_8px] shadow-emerald-500/70',
    bar: 'bg-emerald-500',
  },
  Blocked: {
    dot: 'bg-amber-400 ring-4 ring-amber-400/15 shadow-[0_0_8px] shadow-amber-400/70',
    bar: 'bg-amber-400',
  },
  Completed: {
    dot: 'bg-slate-500 ring-4 ring-slate-500/15',
    bar: 'bg-slate-500',
  },
};
const getStatusStyle = (status) => STATUS_STYLES[status] || STATUS_STYLES.Active;

// Hitlist card states. The active card gets a solid elevated background,
// full opacity, and a bright indigo left accent so the open project is obvious.
const HITLIST_CLASSES = {
  base: 'hitlist-item group block w-full text-left cursor-pointer rounded-md border-l-4 pl-3 pr-3 py-3 transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500',
  active: 'bg-slate-800 border-indigo-500 opacity-100 shadow-lg shadow-black/20',
  inactive: 'bg-transparent border-transparent opacity-70 hover:opacity-100 hover:bg-slate-800/50',
};

// ---------------------------------------------------------------------------
// INITIALIZATION
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  try {
    initClock();
    initTabs();
    initEventListeners();
    await loadUsers();
  } catch (err) {
    console.error('Initialization error:', err);
  }
  loadProjects(true); // Initial load and select first project
});

// Live Clock in Top Navigation
function initClock() {
  const clockEl = document.getElementById('live-clock');
  function update() {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  update();
  setInterval(update, 1000);
}

// ---------------------------------------------------------------------------
// TOAST NOTIFICATIONS
// ---------------------------------------------------------------------------
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'pointer-events-auto flex items-center gap-3 max-w-sm pl-3 pr-4 py-3 rounded-lg bg-slate-800 ring-1 ring-white/5 shadow-2xl shadow-black/40 text-sm font-medium text-slate-200 transition-all duration-300';

  const iconSvg = type === 'success'
    ? `<span class="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-500/15 shrink-0"><svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"></path></svg></span>`
    : type === 'error'
    ? `<span class="flex items-center justify-center w-6 h-6 rounded-full bg-red-500/15 shrink-0"><svg class="w-3.5 h-3.5 text-red-400" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path></svg></span>`
    : `<span class="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-500/15 shrink-0"><svg class="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"></path></svg></span>`;

  toast.innerHTML = `${iconSvg}<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ---------------------------------------------------------------------------
// TAB MANAGEMENT
// ---------------------------------------------------------------------------
function initTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });
}

function switchTab(tabKey) {
  state.activeTab = tabKey;

  // Active styling is declared in index.html via `aria-selected:` and
  // `group-aria-selected:` variants — we only flip the attribute here.
  document.querySelectorAll('.tab-btn').forEach(btn => {
    const isTarget = btn.getAttribute('data-tab') === tabKey;
    btn.setAttribute('aria-selected', isTarget ? 'true' : 'false');
    btn.tabIndex = isTarget ? 0 : -1;
  });

  // Toggle panels
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.add('hidden');
  });

  const activePanel = document.getElementById(`tab-panel-${tabKey}`);
  if (activePanel) {
    activePanel.classList.remove('hidden');
  }
}

// ---------------------------------------------------------------------------
// PROJECT LOADING & HITLIST SIDEBAR
// ---------------------------------------------------------------------------
async function loadProjects(selectFirst = false) {
  try {
    const res = await fetch('/api/projects');
    if (!res.ok) throw new Error('Failed to load projects');
    const data = await res.json();
    state.projects = data;
    filterProjects();

    if (selectFirst && state.projects.length > 0) {
      selectProject(state.projects[0].ID);
    } else if (state.activeProjectId) {
      // Re-fetch active project data if selected
      const exists = state.projects.some(p => p.ID === state.activeProjectId);
      if (exists) {
        selectProject(state.activeProjectId, false);
      } else if (state.projects.length > 0) {
        selectProject(state.projects[0].ID);
      } else {
        clearActiveProject();
      }
    } else if (state.projects.length === 0) {
      clearActiveProject();
    }
  } catch (err) {
    console.error(err);
    showToast(err.message, 'error');
  }
}

function filterProjects() {
  const query = (document.getElementById('search-projects-input').value || '').toLowerCase().trim();
  if (!query) {
    state.filteredProjects = [...state.projects];
  } else {
    state.filteredProjects = state.projects.filter(p =>
      p.Name.toLowerCase().includes(query) ||
      p.Contractor_Name.toLowerCase().includes(query) ||
      p.Status.toLowerCase().includes(query)
    );
  }
  renderHitlist();
}

function renderHitlist() {
  const container = document.getElementById('hitlist-container');
  const countEl = document.getElementById('hitlist-count');
  countEl.textContent = state.projects.length;

  if (state.filteredProjects.length === 0) {
    container.innerHTML = `
      <div class="px-4 py-10 text-center text-sm text-slate-500">
        No projects match your filter.
      </div>
    `;
    return;
  }

  container.innerHTML = state.filteredProjects.map(proj => {
    const isSelected = proj.ID === state.activeProjectId;
    const status = getStatusStyle(proj.Status);
    const pct = proj.Progress_Percentage;

    const stateClass = isSelected ? HITLIST_CLASSES.active : HITLIST_CLASSES.inactive;
    const nameClass = isSelected ? 'text-white' : 'text-slate-200';
    const pctClass = pct === 100 ? 'text-emerald-400' : isSelected ? 'text-indigo-300' : 'text-slate-400';
    const barClass = pct === 100 ? 'bg-emerald-500' : proj.Status === 'Blocked' ? 'bg-amber-400' : 'bg-indigo-500';
    const trackClass = isSelected ? 'bg-slate-700/60' : 'bg-slate-800';

    return `
      <div role="button" tabindex="0" data-project-id="${proj.ID}" ${isSelected ? 'aria-current="true"' : ''}
           class="${HITLIST_CLASSES.base} ${stateClass}" title="${escapeHtml(proj.Name)}">

        <!-- Row 1: status dot · name (truncates) · percent (pinned right) -->
        <div class="flex items-center gap-3 min-w-0">
          <span class="w-2.5 h-2.5 shrink-0 rounded-full ${status.dot}" aria-label="${escapeHtml(proj.Status)}"></span>
          <span class="flex-1 min-w-0 truncate text-sm font-medium ${nameClass}">${escapeHtml(proj.Name)}</span>
          <span class="shrink-0 text-xs font-semibold tabular-nums ${pctClass}">${pct}%</span>
        </div>

        <!-- Row 2: contractor (truncates) · step count (pinned right, never wraps) -->
        <div class="flex items-center gap-3 min-w-0 mt-1 pl-[1.375rem] text-xs">
          <span class="flex-1 min-w-0 truncate text-slate-400">${escapeHtml(proj.Contractor_Name)}</span>
          <span class="shrink-0 whitespace-nowrap tabular-nums text-slate-500">${proj.Completed_Steps}/${proj.Total_Steps} steps</span>
        </div>

        <!-- Row 3: mini progress -->
        <div class="mt-2.5 ml-[1.375rem] h-1 rounded-full overflow-hidden ${trackClass}">
          <div class="h-full rounded-full ${barClass} transition-all duration-500" style="width: ${pct}%;"></div>
        </div>
      </div>
    `;
  }).join('');

  // Attach click + keyboard events
  container.querySelectorAll('.hitlist-item').forEach(el => {
    const pid = parseInt(el.getAttribute('data-project-id'), 10);
    el.addEventListener('click', () => selectProject(pid));
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        selectProject(pid);
      }
    });
  });
}

async function selectProject(projectId, resetTab = false) {
  state.activeProjectId = projectId;
  renderHitlist();

  try {
    const res = await fetch(`/api/projects/${projectId}`);
    if (!res.ok) throw new Error('Failed to load project details');
    const data = await res.json();
    state.activeProjectData = data;

    renderActiveProject(resetTab);
  } catch (err) {
    console.error(err);
    showToast(err.message, 'error');
  }
}

function clearActiveProject() {
  state.activeProjectId = null;
  state.activeProjectData = null;
  document.getElementById('active-project-stage').classList.add('hidden');
  document.getElementById('empty-stage').classList.remove('hidden');
}

// ---------------------------------------------------------------------------
// RENDER MAIN STAGE & ACTIVE PROJECT
// ---------------------------------------------------------------------------
function renderActiveProject(resetTab = false) {
  const p = state.activeProjectData;
  if (!p) return;

  document.getElementById('empty-stage').classList.add('hidden');
  document.getElementById('active-project-stage').classList.remove('hidden');

  if (resetTab) {
    switchTab('overview');
  }

  // Header updates
  document.getElementById('proj-header-name').textContent = p.Name;
  document.getElementById('proj-header-contractor').textContent = p.Contractor_Name;
  document.getElementById('proj-header-id').textContent = `ID: #${p.ID}`;
  document.getElementById('proj-header-status-select').value = p.Status;

  // Header status dot (shares the glow styling used in the Hitlist)
  const dotEl = document.getElementById('proj-header-status-dot');
  dotEl.className = `w-3 h-3 shrink-0 rounded-full ${getStatusStyle(p.Status).dot}`;

  // Badges on tabs
  document.getElementById('tab-badge-steps').textContent = `${p.Completed_Steps}/${p.Total_Steps}`;
  document.getElementById('tab-badge-attachments').textContent = `${p.Attachments.length}`;
  document.getElementById('tab-badge-hours').textContent = `${p.Total_Hours_Logged}h`;

  // Render Tab 1: Overview
  renderTabOverview(p);

  // Render Tab 2: Phases & Steps
  renderTabPhases(p);

  // Render Tab 3: Attachments
  renderTabAttachments(p);

  // Render Tab 4: Time Tracking
  renderTabTimeTrack(p);
}

// Soft pill used for Reported / Unreported flags across lists
function reportedBadge(isReported) {
  return isReported
    ? '<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-slate-800 text-[10px] font-medium text-slate-400">Reported</span>'
    : '<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-amber-400/10 text-[10px] font-medium text-amber-300">Unreported</span>';
}

// ---------------------------------------------------------------------------
// TAB 1: OVERVIEW RENDERING
// ---------------------------------------------------------------------------
function updateContactLinks(projectName, email, phone) {
  const mailLink = document.getElementById('pm-mail-link');
  const teamsLink = document.getElementById('pm-teams-link');
  const phoneLink = document.getElementById('contractor-phone-link');

  if (mailLink && teamsLink) {
    if (email && email.trim()) {
      const cleanEmail = email.trim();
      mailLink.href = `mailto:${cleanEmail}?subject=${encodeURIComponent(projectName || 'Project Coordination')}`;
      teamsLink.href = `https://teams.microsoft.com/l/chat/0/0?users=${encodeURIComponent(cleanEmail)}`;
      mailLink.classList.remove('hidden');
      teamsLink.classList.remove('hidden');
    } else {
      mailLink.classList.add('hidden');
      teamsLink.classList.add('hidden');
    }
  }

  if (phoneLink) {
    if (phone && phone.trim()) {
      const cleanPhone = phone.trim().replace(/[^\d+]/g, '');
      phoneLink.href = `tel:${cleanPhone}`;
      phoneLink.classList.remove('hidden');
    } else {
      phoneLink.classList.add('hidden');
    }
  }
}

function renderTabOverview(p) {
  // Progress Bar
  const percent = p.Progress_Percentage;
  document.getElementById('overview-progress-percent').textContent = `${percent}%`;
  document.getElementById('overview-progress-ratio').textContent = `${p.Completed_Steps} of ${p.Total_Steps} steps completed`;
  const barEl = document.getElementById('overview-progress-bar');
  barEl.style.width = `${percent}%`;
  barEl.className = percent === 100
    ? 'h-full rounded-full bg-emerald-500 transition-all duration-500 ease-out'
    : 'h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500 ease-out';

  // Project Notes & Contractor Edit inputs
  document.getElementById('edit-contractor-input').value = p.Contractor_Name || '';
  document.getElementById('edit-notes-textarea').value = p.Notes || '';

  // Project Manager & Contractor Lead inputs
  const pmNameInput = document.getElementById('edit-pm-name-input');
  const pmEmailInput = document.getElementById('edit-pm-email-input');
  const leadNameInput = document.getElementById('edit-contractor-lead-input');
  const leadPhoneInput = document.getElementById('edit-contractor-phone-input');

  if (pmNameInput) pmNameInput.value = p.Project_Manager_Name || '';
  if (pmEmailInput) pmEmailInput.value = p.Project_Manager_Email || '';
  if (leadNameInput) leadNameInput.value = p.Contractor_Lead_Name || '';
  if (leadPhoneInput) leadPhoneInput.value = p.Contractor_Lead_Phone || '';

  updateContactLinks(p.Name, p.Project_Manager_Email, p.Contractor_Lead_Phone);

  // Updates Feed
  const updatesContainer = document.getElementById('overview-updates-list');
  if (p.Updates.length === 0) {
    updatesContainer.innerHTML = `<div class="text-sm text-slate-500 text-center py-8">No field updates posted for this project yet.</div>`;
    return;
  }

  updatesContainer.innerHTML = p.Updates.map(u => {
    return `
      <div class="group py-3 border-b border-slate-800 last:border-b-0">
        <div class="flex items-center justify-between gap-3 mb-1">
          <div class="flex items-center gap-2 min-w-0 flex-wrap">
            <span class="text-xs text-slate-500 tabular-nums whitespace-nowrap">${u.Timestamp}</span>
            ${u.Author_Name ? `<span class="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">${escapeHtml(u.Author_Name)}</span>` : ''}
            ${reportedBadge(u.Reported_Flag)}
          </div>
          <button data-update-id="${u.ID}" title="Delete update" class="btn-delete-update opacity-0 group-hover:opacity-100 focus-visible:opacity-100 shrink-0 p-1 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors">
            ${ICONS.trash}
          </button>
        </div>
        <div class="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap select-text">${escapeHtml(u.Note_Text)}</div>
      </div>
    `;
  }).join('');

  // Attach delete listeners
  updatesContainer.querySelectorAll('.btn-delete-update').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const uid = btn.getAttribute('data-update-id');
      if (confirm('Delete this field update?')) {
        await deleteUpdate(uid);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// TAB 2: PHASES & STEPS (ACCORDION) RENDERING
// ---------------------------------------------------------------------------
function renderTabPhases(p) {
  const container = document.getElementById('phases-accordion-container');
  if (p.Phases.length === 0) {
    container.innerHTML = `
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-xs text-slate-500">
        No phases defined yet. Click "Add New Phase" above to begin.
      </div>
    `;
    return;
  }

  container.innerHTML = p.Phases.map(phase => {
    const isCollapsed = state.collapsedPhases.has(phase.ID);
    const stepsCount = phase.Steps.length;
    const completedCount = phase.Steps.filter(s => s.Is_Completed).length;
    const phasePercent = stepsCount > 0 ? Math.round((completedCount / stepsCount) * 100) : 0;

    return `
      <div class="phase-card mb-4" data-phase-id="${phase.ID}">
        
        <!-- Accordion Header -->
        <div class="phase-header bg-slate-800/50 hover:bg-slate-800/80 p-4 rounded-t-md flex items-center justify-between cursor-pointer transition select-none group border-b border-slate-800/50">
          <div class="flex items-center space-x-3 flex-1 min-w-0 mr-3">
            <span class="phase-toggle-icon transform ${isCollapsed ? '-rotate-90' : 'rotate-0'} transition-transform duration-200 text-slate-400 group-hover:text-slate-300 shrink-0">
              ${ICONS.chevronDown}
            </span>
            <div class="phase-display-wrapper flex items-center gap-2 flex-1 min-w-0">
              <span class="text-sm font-semibold text-slate-200 tracking-wide truncate phase-title-text">${escapeHtml(phase.Phase_Name)}</span>
              <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-400 shrink-0">
                ${completedCount}/${stepsCount} steps (${phasePercent}%)
              </span>
            </div>
            <!-- Inline Edit Form -->
            <form class="phase-edit-form hidden flex items-center gap-2 flex-1 min-w-0" data-phase-id="${phase.ID}">
              <input type="text" required class="input-phase-name-edit bg-slate-950/90 border border-indigo-500 rounded px-2.5 py-1 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-400 flex-1 min-w-[140px]" value="${escapeHtml(phase.Phase_Name)}">
              <button type="submit" class="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow transition shrink-0">
                Save
              </button>
              <button type="button" class="btn-cancel-phase-edit px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition shrink-0">
                Cancel
              </button>
            </form>
          </div>

          <div class="flex items-center space-x-1 shrink-0">
            <button data-phase-id="${phase.ID}" data-phase-name="${escapeHtml(phase.Phase_Name)}" title="Edit Phase Name" class="btn-edit-phase text-slate-500 hover:text-indigo-400 p-1.5 rounded hover:bg-slate-800 transition">
              ${ICONS.pencil}
            </button>
            <button data-phase-id="${phase.ID}" title="Delete Phase" class="btn-delete-phase text-slate-500 hover:text-red-400 p-1.5 rounded hover:bg-slate-800 transition">
              ${ICONS.trash}
            </button>
          </div>
        </div>

        <!-- Accordion Content -->
        <div class="phase-steps-content bg-slate-900 rounded-b-md shadow-sm ${isCollapsed ? 'hidden' : ''}">
          
          <!-- Phase Notes & Scope Area (Independent for each phase) -->
          <div class="px-4 py-3 bg-slate-950/40 border-b border-slate-800/80">
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"></path></svg>
                Phase Notes &amp; Scope
              </span>
              <button data-phase-id="${phase.ID}" class="btn-save-phase-notes text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold transition px-2 py-0.5 rounded hover:bg-indigo-500/10">
                Save Phase Notes
              </button>
            </div>
            <textarea data-phase-id="${phase.ID}" rows="2" placeholder="Specific notes, safety lockouts, or handover criteria for this phase..." class="input-phase-notes w-full rounded bg-slate-950/80 border border-slate-800 px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition resize-y">${escapeHtml(phase.Notes || '')}</textarea>
          </div>

          <!-- Steps Checklist -->
          <div class="steps-list flex flex-col">
            ${
              phase.Steps.map(step => {
                return `
                  <div class="group flex items-center justify-between p-3 border-b border-slate-800 transition hover:bg-slate-800/30" data-step-id="${step.ID}">
                    
                    <!-- 1. ONLY Checkbox toggles complete status -->
                    <div class="shrink-0 pr-3 py-1 flex items-center">
                      <input type="checkbox" data-step-id="${step.ID}" class="step-checkbox custom-checkbox cursor-pointer" ${step.Is_Completed ? 'checked' : ''} aria-label="Mark step complete">
                    </div>

                    <!-- 2. Clicking elsewhere on the step opens details modal -->
                    <div class="step-details-trigger flex-1 min-w-0 cursor-pointer py-1 select-none" data-step-id="${step.ID}" data-phase-id="${phase.ID}" title="Click to view & edit step details">
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-sm font-medium text-slate-200 hover:text-indigo-300 transition ${step.Is_Completed ? 'line-through text-slate-500 hover:text-slate-400' : ''}">
                          ${escapeHtml(step.Step_Name)}
                        </span>
                        ${
                          step.Details
                            ? `<span class="inline-flex items-center gap-1 text-[11px] font-normal text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">
                                 <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"></path></svg>
                                 Details
                               </span>`
                            : ''
                        }
                      </div>
                      ${
                        step.Details
                          ? `<p class="text-xs text-slate-400 truncate mt-0.5">${escapeHtml(step.Details)}</p>`
                          : ''
                      }
                    </div>

                    <!-- 3. Right Status and Actions -->
                    <div class="flex items-center space-x-2 shrink-0 pl-3">
                      ${
                        step.Is_Completed
                          ? `<span class="text-[10px] font-mono text-emerald-500/80 mr-1 hidden sm:inline">${step.Completed_At ? step.Completed_At.split(' ')[1] : 'Done'}${step.Completed_By ? ` &bull; ${escapeHtml(step.Completed_By)}` : ''}</span>`
                          : ''
                      }
                      <button data-step-id="${step.ID}" title="Delete step" class="btn-delete-step text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 p-1.5 rounded transition">
                        ${ICONS.trash}
                      </button>
                    </div>
                  </div>
                `;
              }).join('')
            }
          </div>

          <!-- Inline Quick Step Input -->
          <div class="flex items-center px-3 py-2.5 group hover:bg-slate-800/20 rounded-b-md transition">
            <span class="text-slate-600 mr-2 ml-1 opacity-50 group-hover:opacity-100 transition">${ICONS.plus}</span>
            <input type="text" data-phase-id="${phase.ID}" placeholder="Add new step..." class="input-inline-step flex-1 bg-transparent border-none text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:ring-0">
            <button data-phase-id="${phase.ID}" class="btn-inline-add-step opacity-0 group-focus-within:opacity-100 group-hover:opacity-100 text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition px-2 py-1">
              Add
            </button>
          </div>

        </div>

      </div>
    `;
  }).join('');

  // Attach Accordion Toggle listeners
  container.querySelectorAll('.phase-header').forEach(hdr => {
    hdr.addEventListener('click', (e) => {
      // Don't toggle if delete button, edit button, or edit form was clicked
      if (e.target.closest('.btn-delete-phase') || e.target.closest('.btn-edit-phase') || e.target.closest('.phase-edit-form')) return;

      const phaseCard = hdr.closest('.phase-card');
      const phaseId = parseInt(phaseCard.getAttribute('data-phase-id'), 10);
      const content = phaseCard.querySelector('.phase-steps-content');
      const icon = hdr.querySelector('.phase-toggle-icon');

      if (state.collapsedPhases.has(phaseId)) {
        state.collapsedPhases.delete(phaseId);
        content.classList.remove('hidden');
        icon.classList.remove('-rotate-90');
      } else {
        state.collapsedPhases.add(phaseId);
        content.classList.add('hidden');
        icon.classList.add('-rotate-90');
      }
    });
  });

  // Attach Save Phase Notes listeners
  container.querySelectorAll('.btn-save-phase-notes').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const phaseId = parseInt(btn.getAttribute('data-phase-id'), 10);
      const textarea = container.querySelector(`.input-phase-notes[data-phase-id="${phaseId}"]`);
      if (textarea) {
        await savePhaseNotes(phaseId, textarea.value.trim());
      }
    });
  });

  // Attach Step Checkbox listeners (ONLY checkbox updates completion)
  container.querySelectorAll('.step-checkbox').forEach(chk => {
    chk.addEventListener('change', async (e) => {
      e.stopPropagation();
      const stepId = chk.getAttribute('data-step-id');
      const isCompleted = chk.checked;
      await toggleStep(stepId, isCompleted);
    });
  });

  // Attach Step Details Modal Trigger listeners
  container.querySelectorAll('.step-details-trigger').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const stepId = parseInt(trigger.getAttribute('data-step-id'), 10);
      const phaseId = parseInt(trigger.getAttribute('data-phase-id'), 10);
      openStepDetailsModal(phaseId, stepId);
    });
  });

  // Attach Step Delete listeners
  container.querySelectorAll('.btn-delete-step').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const stepId = btn.getAttribute('data-step-id');
      await deleteStep(stepId);
    });
  });

  // Attach Phase Delete listeners
  container.querySelectorAll('.btn-delete-phase').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const phaseId = btn.getAttribute('data-phase-id');
      if (confirm('Delete this phase and all its steps?')) {
        await deletePhase(phaseId);
      }
    });
  });

  // Attach Phase Edit listeners
  container.querySelectorAll('.btn-edit-phase').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const phaseCard = btn.closest('.phase-card');
      if (!phaseCard) return;
      const displayWrapper = phaseCard.querySelector('.phase-display-wrapper');
      const editForm = phaseCard.querySelector('.phase-edit-form');
      const input = editForm ? editForm.querySelector('.input-phase-name-edit') : null;

      if (displayWrapper && editForm && input) {
        const isEditing = !editForm.classList.contains('hidden');
        if (isEditing) {
          editForm.classList.add('hidden');
          displayWrapper.classList.remove('hidden');
        } else {
          displayWrapper.classList.add('hidden');
          editForm.classList.remove('hidden');
          input.focus();
          input.select();
        }
      }
    });
  });

  // Cancel Phase Edit
  container.querySelectorAll('.btn-cancel-phase-edit').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const phaseCard = btn.closest('.phase-card');
      if (!phaseCard) return;
      const displayWrapper = phaseCard.querySelector('.phase-display-wrapper');
      const editForm = phaseCard.querySelector('.phase-edit-form');
      const input = editForm ? editForm.querySelector('.input-phase-name-edit') : null;
      const originalName = phaseCard.querySelector('.btn-edit-phase')?.getAttribute('data-phase-name') || '';

      if (displayWrapper && editForm) {
        if (input) input.value = originalName;
        editForm.classList.add('hidden');
        displayWrapper.classList.remove('hidden');
      }
    });
  });

  // Submit Phase Edit
  container.querySelectorAll('.phase-edit-form').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const phaseId = form.getAttribute('data-phase-id');
      const input = form.querySelector('.input-phase-name-edit');
      const newName = input ? input.value.trim() : '';
      if (!newName) return;
      await renamePhase(phaseId, newName);
    });

    const input = form.querySelector('.input-phase-name-edit');
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          const cancelBtn = form.querySelector('.btn-cancel-phase-edit');
          if (cancelBtn) cancelBtn.click();
        }
      });
    }
  });

  // Attach Inline Add Step inputs
  container.querySelectorAll('.btn-inline-add-step').forEach(btn => {
    btn.addEventListener('click', async () => {
      const phaseId = btn.getAttribute('data-phase-id');
      const input = container.querySelector(`.input-inline-step[data-phase-id="${phaseId}"]`);
      if (input && input.value.trim()) {
        await addStep(phaseId, input.value.trim());
        input.value = '';
      }
    });
  });

  container.querySelectorAll('.input-inline-step').forEach(input => {
    input.addEventListener('keydown', async (e) => {
      if (e.key === 'Enter') {
        const phaseId = input.getAttribute('data-phase-id');
        if (input.value.trim()) {
          await addStep(phaseId, input.value.trim());
          input.value = '';
        }
      }
    });
  });
}

// ---------------------------------------------------------------------------
// TAB 3: ATTACHMENTS RENDERING
// ---------------------------------------------------------------------------
function renderTabAttachments(p) {
  const container = document.getElementById('attachments-list');
  const countLabel = document.getElementById('attachments-count-label');
  countLabel.textContent = `${p.Attachments.length} file${p.Attachments.length === 1 ? '' : 's'}`;

  if (p.Attachments.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 text-center py-8">No attachments uploaded yet. Drop files above to upload.</div>`;
    return;
  }

  container.innerHTML = p.Attachments.map(att => {
    const sizeKb = (att.File_Size / 1024).toFixed(1);
    return `
      <div class="group flex items-center justify-between p-3 bg-slate-900 border-b border-slate-800 last:border-b-0 transition hover:bg-slate-800/30">
        <div class="flex items-center space-x-3 min-w-0 pr-3">
          ${ICONS.paperclip}
          <div class="min-w-0">
            <div class="text-sm font-medium text-slate-200 truncate">${escapeHtml(att.File_Name)}</div>
            <div class="flex items-center space-x-2 text-[10px] text-slate-500 font-mono mt-0.5">
              <span>${sizeKb} KB</span>
              <span>&bull;</span>
              <span>${att.Uploaded_At}</span>
              <span>&bull;</span>
              ${
                att.Reported_Flag
                  ? '<span class="text-slate-400 font-sans">Reported in Outlook</span>'
                  : '<span class="text-amber-500 font-sans font-semibold">Unreported</span>'
              }
            </div>
          </div>
        </div>

        <div class="flex items-center space-x-1.5 flex-shrink-0 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
          <button data-att-id="${att.ID}" title="Open locally with Windows default app" class="btn-open-att px-2 py-1 bg-slate-800 hover:bg-slate-700 text-sky-400 rounded text-xs font-semibold flex items-center space-x-1 transition">
            ${ICONS.arrowTopRightOnSquare}
            <span>Open</span>
          </button>
          <a href="/api/attachments/${att.ID}/download" title="Download copy" download class="p-1.5 text-slate-500 hover:text-white rounded hover:bg-slate-800 transition">
            ${ICONS.arrowDownTray}
          </a>
          <button data-att-id="${att.ID}" title="Delete file" class="btn-delete-att p-1.5 text-slate-500 hover:text-red-400 rounded hover:bg-slate-800 transition">
            ${ICONS.trash}
          </button>
        </div>
      </div>
    `;
  }).join('');

  // Open locally buttons
  container.querySelectorAll('.btn-open-att').forEach(btn => {
    btn.addEventListener('click', async () => {
      const attId = btn.getAttribute('data-att-id');
      try {
        const res = await fetch(`/api/attachments/${attId}/open`);
        if (!res.ok) throw new Error('Failed to open attachment');
        showToast('File opened in default Windows app');
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  });

  // Delete attachment buttons
  container.querySelectorAll('.btn-delete-att').forEach(btn => {
    btn.addEventListener('click', async () => {
      const attId = btn.getAttribute('data-att-id');
      if (confirm('Delete this attachment?')) {
        await deleteAttachment(attId);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// TAB 4: TIME TRACKING RENDERING
// ---------------------------------------------------------------------------
function renderTabTimeTrack(p) {
  const container = document.getElementById('timelogs-list');
  const totalHoursEl = document.getElementById('timetrack-total-hours');
  totalHoursEl.textContent = `${p.Total_Hours_Logged} hrs`;

  if (p.Time_Logs.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 text-center py-10">No time logged for this project yet. Use the form on the left.</div>`;
    return;
  }

  container.innerHTML = p.Time_Logs.map(tl => {
    return `
      <div class="group p-4 bg-slate-900 border-b border-slate-800 last:border-b-0 transition hover:bg-slate-800/30">
        <div class="flex items-center justify-between mb-1">
          <div class="flex items-center space-x-2 flex-wrap gap-y-1">
            <span class="text-sm font-bold text-sky-400 font-mono">${tl.Hours_Logged} hrs</span>
            <span class="text-xs text-slate-400 font-medium">(${tl.Start_Time} &ndash; ${tl.End_Time})</span>
            ${tl.Author_Name ? `<span class="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">${escapeHtml(tl.Author_Name)}</span>` : ''}
            ${
              tl.Reported_Flag
                ? '<span class="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">Reported</span>'
                : '<span class="text-[10px] px-1.5 py-0.2 rounded bg-amber-950/50 text-amber-500 border border-amber-800/30">Unreported</span>'
            }
          </div>
          <button data-timelog-id="${tl.ID}" class="btn-delete-timelog text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 p-1 rounded transition">
            ${ICONS.trash}
          </button>
        </div>
        <div class="text-sm text-slate-300 leading-snug mt-1">${escapeHtml(tl.Description || 'Standard shift activity')}</div>
        <div class="text-[10px] font-mono text-slate-600 mt-2">Logged on: ${tl.Created_At}</div>
      </div>
    `;
  }).join('');

  container.querySelectorAll('.btn-delete-timelog').forEach(btn => {
    btn.addEventListener('click', async () => {
      const tid = btn.getAttribute('data-timelog-id');
      if (confirm('Delete this time log entry?')) {
        await deleteTimeLog(tid);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// CRUD OPERATIONS (API CALLS)
// ---------------------------------------------------------------------------

// 1. Projects
async function updateProjectStatus(newStatus) {
  if (!state.activeProjectId) return;
  try {
    const res = await fetch(`/api/projects/${state.activeProjectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Status: newStatus }),
    });
    if (!res.ok) throw new Error('Failed to update project status');
    showToast(`Status updated to ${newStatus}`);
    await loadProjects(false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function saveProjectMetadata() {
  if (!state.activeProjectId) return;
  const contractor = document.getElementById('edit-contractor-input').value.trim();
  const notes = document.getElementById('edit-notes-textarea').value.trim();
  const pmName = (document.getElementById('edit-pm-name-input')?.value || '').trim();
  const pmEmail = (document.getElementById('edit-pm-email-input')?.value || '').trim();
  const leadName = (document.getElementById('edit-contractor-lead-input')?.value || '').trim();
  const leadPhone = (document.getElementById('edit-contractor-phone-input')?.value || '').trim();

  try {
    const res = await fetch(`/api/projects/${state.activeProjectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        Contractor_Name: contractor,
        Notes: notes,
        Project_Manager_Name: pmName,
        Project_Manager_Email: pmEmail,
        Contractor_Lead_Name: leadName,
        Contractor_Lead_Phone: leadPhone,
      }),
    });
    if (!res.ok) throw new Error('Failed to update project metadata');
    showToast('Project notes and contacts saved');
    await loadProjects(false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteProject(projectId) {
  try {
    const res = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete project');
    showToast('Project deleted');
    await loadProjects(true);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 2. Phases & Steps
async function addPhase(phaseName, notes = '') {
  if (!state.activeProjectId) return;
  try {
    const res = await fetch(`/api/projects/${state.activeProjectId}/phases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Phase_Name: phaseName, Notes: notes }),
    });
    if (!res.ok) throw new Error('Failed to add phase');
    showToast('Phase added successfully');
    await selectProject(state.activeProjectId, false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function savePhaseNotes(phaseId, notes) {
  try {
    const res = await fetch(`/api/phases/${phaseId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Notes: notes }),
    });
    if (!res.ok) throw new Error('Failed to save phase notes');
    showToast('Phase notes saved');
    await selectProject(state.activeProjectId, false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function renamePhase(phaseId, newName) {
  try {
    const res = await fetch(`/api/phases/${phaseId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Phase_Name: newName }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Failed to rename phase');

    showToast('Phase renamed', 'success');
    await selectProject(state.activeProjectId, false);
    await loadProjects(false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deletePhase(phaseId) {
  try {
    const res = await fetch(`/api/phases/${phaseId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete phase');
    showToast('Phase deleted');
    await selectProject(state.activeProjectId, false);
    await loadProjects(false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function addStep(phaseId, stepName, details = '') {
  try {
    const res = await fetch(`/api/phases/${phaseId}/steps`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Step_Name: stepName, Details: details }),
    });
    if (!res.ok) throw new Error('Failed to add step');
    showToast('Step added');
    await selectProject(state.activeProjectId, false);
    await loadProjects(false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function updateStep(stepId, stepName, details) {
  try {
    const res = await fetch(`/api/steps/${stepId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Step_Name: stepName, Details: details }),
    });
    if (!res.ok) throw new Error('Failed to update step details');
    showToast('Step details saved');
    await selectProject(state.activeProjectId, false);
    await loadProjects(false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openStepDetailsModal(phaseId, stepId) {
  const p = state.activeProjectData;
  if (!p) return;
  const phase = p.Phases.find(ph => ph.ID === phaseId);
  if (!phase) return;
  const step = phase.Steps.find(s => s.ID === stepId);
  if (!step) return;

  document.getElementById('modal-step-id').value = step.ID;
  document.getElementById('modal-step-phase-label').textContent = phase.Phase_Name;
  document.getElementById('modal-step-name-input').value = step.Step_Name;
  document.getElementById('modal-step-details-textarea').value = step.Details || '';

  const statusBadge = document.getElementById('modal-step-status-badge');
  const timeLabel = document.getElementById('modal-step-completed-time');

  if (step.Is_Completed) {
    statusBadge.className = 'px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/20';
    statusBadge.textContent = 'Completed';
    const byStr = step.Completed_By ? ` by ${step.Completed_By}` : '';
    timeLabel.textContent = step.Completed_At ? `Completed: ${step.Completed_At}${byStr}` : `Completed${byStr}`;
  } else {
    statusBadge.className = 'px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-400 border border-slate-700/50';
    statusBadge.textContent = 'Pending';
    timeLabel.textContent = '';
  }

  document.getElementById('modal-step-details').classList.remove('hidden');
}

function closeStepDetailsModal() {
  document.getElementById('modal-step-details').classList.add('hidden');
}

async function toggleStep(stepId, isCompleted) {
  const activeUser = getActiveUser();
  try {
    const res = await fetch(`/api/steps/${stepId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        Is_Completed: isCompleted,
        Completed_By: isCompleted && activeUser ? activeUser.Name : '',
      }),
    });
    if (!res.ok) throw new Error('Failed to update step');

    // Immediately reload project data to recalculate progress bar accurately
    await selectProject(state.activeProjectId, false);
    await loadProjects(false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteStep(stepId) {
  try {
    const res = await fetch(`/api/steps/${stepId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete step');
    showToast('Step deleted');
    await selectProject(state.activeProjectId, false);
    await loadProjects(false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 3. Updates
async function postUpdate() {
  if (!state.activeProjectId) return;
  const input = document.getElementById('new-update-input');
  const text = input.value.trim();
  if (!text) return;

  const activeUser = getActiveUser();
  try {
    const res = await fetch(`/api/projects/${state.activeProjectId}/updates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        Note_Text: text,
        User_ID: activeUser ? activeUser.ID : null,
        Author_Name: activeUser ? activeUser.Name : '',
      }),
    });
    if (!res.ok) throw new Error('Failed to post update');
    input.value = '';
    showToast('Field note posted');
    await selectProject(state.activeProjectId, false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteUpdate(updateId) {
  try {
    const res = await fetch(`/api/updates/${updateId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete update');
    showToast('Update deleted');
    await selectProject(state.activeProjectId, false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 4. Attachments (Upload & Delete)
async function uploadFiles(files) {
  if (!state.activeProjectId || !files || files.length === 0) return;
  let successCount = 0;

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`/api/projects/${state.activeProjectId}/attachments`, {
        method: 'POST',
        body: formData,
      });
      if (res.ok) successCount++;
    } catch (err) {
      console.error(err);
    }
  }

  if (successCount > 0) {
    showToast(`${successCount} file(s) uploaded successfully`);
    await selectProject(state.activeProjectId, false);
  } else {
    showToast('Failed to upload files', 'error');
  }
}

async function deleteAttachment(attId) {
  try {
    const res = await fetch(`/api/attachments/${attId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete attachment');
    showToast('Attachment deleted');
    await selectProject(state.activeProjectId, false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 5. Time Tracking
async function logTime(startTime, endTime, hours, desc) {
  if (!state.activeProjectId) return;
  const activeUser = getActiveUser();
  try {
    const res = await fetch(`/api/projects/${state.activeProjectId}/time-logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        Start_Time: startTime,
        End_Time: endTime,
        Hours_Logged: parseFloat(hours),
        Description: desc,
        User_ID: activeUser ? activeUser.ID : null,
        Author_Name: activeUser ? activeUser.Name : '',
      }),
    });
    if (!res.ok) throw new Error('Failed to record time log');
    showToast('Shift time window recorded');
    await selectProject(state.activeProjectId, false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteTimeLog(logId) {
  try {
    const res = await fetch(`/api/time-logs/${logId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete time log');
    showToast('Time log entry deleted');
    await selectProject(state.activeProjectId, false);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ---------------------------------------------------------------------------
// END OF SHIFT & OUTLOOK INTEGRATION
// ---------------------------------------------------------------------------
async function openShiftModal() {
  const modal = document.getElementById('modal-shift');
  modal.classList.remove('hidden');

  const activeUser = getActiveUser();
  const reportingBadge = document.getElementById('shift-reporting-user-badge');
  if (reportingBadge) {
    reportingBadge.textContent = activeUser ? `${activeUser.Name} (${activeUser.Role || 'Technician'})` : 'Default Technician';
  }

  try {
    const res = await fetch('/api/end-of-shift/summary');
    if (!res.ok) throw new Error('Failed to fetch unreported shift summary');
    const summary = await res.json();
    state.shiftSummaryData = summary;

    // Default selection: if active project exists and is in summary, select it; otherwise select all
    if (state.activeProjectId && summary.projects_overview.some(p => p.ID === state.activeProjectId)) {
      state.shiftSelectedProjectIds = new Set([state.activeProjectId]);
    } else {
      state.shiftSelectedProjectIds = new Set(summary.projects_overview.map(p => p.ID));
    }

    renderShiftProjectsSelector();
    updateShiftModalFilteredView();

  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderShiftProjectsSelector() {
  const container = document.getElementById('shift-projects-selector-container');
  if (!container || !state.shiftSummaryData) return;
  const { projects_overview, steps, time_logs, updates, attachments } = state.shiftSummaryData;

  if (projects_overview.length === 0) {
    container.innerHTML = '<div class="text-xs text-slate-500 italic p-2 text-center">No projects found.</div>';
    return;
  }

  container.innerHTML = projects_overview.map(p => {
    const isChecked = state.shiftSelectedProjectIds.has(p.ID);
    const pSteps = steps.filter(s => s.Project_ID === p.ID).length;
    const pHours = time_logs.filter(t => t.Project_ID === p.ID).reduce((acc, t) => acc + (t.Hours_Logged || 0), 0);
    const pUpdates = updates.filter(u => u.Project_ID === p.ID).length;
    const pAtts = attachments.filter(a => a.Project_ID === p.ID).length;
    const hasActivity = pSteps > 0 || pHours > 0 || pUpdates > 0 || pAtts > 0;

    const statusDot = p.Status === 'Active' ? 'bg-emerald-400' : p.Status === 'Blocked' ? 'bg-amber-400' : 'bg-slate-400';

    const activityBadge = hasActivity
      ? `<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-indigo-500/15 text-indigo-300 border border-indigo-500/20">${pSteps} steps &bull; ${pHours.toFixed(1)}h</span>`
      : `<span class="text-[10px] text-slate-500">Up to date</span>`;

    return `
      <label class="flex items-center justify-between p-2.5 rounded-md bg-slate-900 hover:bg-slate-800/80 border border-slate-800 cursor-pointer transition select-none">
        <div class="flex items-center gap-2.5 min-w-0">
          <input type="checkbox" class="shift-proj-checkbox rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-slate-900" data-project-id="${p.ID}" ${isChecked ? 'checked' : ''}>
          <span class="w-2 h-2 shrink-0 rounded-full ${statusDot}"></span>
          <div class="min-w-0">
            <div class="text-xs font-semibold text-slate-200 truncate">${escapeHtml(p.Name)}</div>
            <div class="text-[10px] text-slate-400 truncate">PM: ${escapeHtml(p.Project_Manager_Name || 'Unassigned')}</div>
          </div>
        </div>
        <div class="shrink-0 text-right pl-2">
          ${activityBadge}
        </div>
      </label>
    `;
  }).join('');

  // Wire individual checkbox listeners
  container.querySelectorAll('.shift-proj-checkbox').forEach(chk => {
    chk.addEventListener('change', (e) => {
      const pid = parseInt(e.target.getAttribute('data-project-id'), 10);
      if (e.target.checked) {
        state.shiftSelectedProjectIds.add(pid);
      } else {
        state.shiftSelectedProjectIds.delete(pid);
      }
      updateShiftModalFilteredView();
    });
  });
}

function updateShiftModalFilteredView() {
  if (!state.shiftSummaryData) return;
  const summary = state.shiftSummaryData;
  const selected = state.shiftSelectedProjectIds;

  const filteredSteps = summary.steps.filter(s => selected.has(s.Project_ID));
  const filteredTimeLogs = summary.time_logs.filter(t => selected.has(t.Project_ID));
  const filteredUpdates = summary.updates.filter(u => selected.has(u.Project_ID));
  const filteredAttachments = summary.attachments.filter(a => selected.has(a.Project_ID));
  const totalHours = Math.round(filteredTimeLogs.reduce((acc, t) => acc + (t.Hours_Logged || 0), 0) * 100) / 100;

  // Update KPI Numbers
  document.getElementById('shift-summary-hours').textContent = totalHours;
  document.getElementById('shift-summary-steps').textContent = filteredSteps.length;
  document.getElementById('shift-summary-updates').textContent = filteredUpdates.length;
  document.getElementById('shift-summary-attachments').textContent = filteredAttachments.length;

  // Update Badges
  document.getElementById('shift-steps-badge').textContent = `${filteredSteps.length} items`;
  document.getElementById('shift-timelogs-badge').textContent = `${filteredTimeLogs.length} items`;
  document.getElementById('shift-updates-badge').textContent = `${filteredUpdates.length} items`;
  document.getElementById('shift-attachments-badge').textContent = `${filteredAttachments.length} items`;

  // Render Completed Steps
  const stepsListEl = document.getElementById('shift-steps-list');
  if (filteredSteps.length === 0) {
    stepsListEl.innerHTML = `<li class="text-slate-500 italic">No completed steps to report for selected project(s).</li>`;
  } else {
    stepsListEl.innerHTML = filteredSteps.map(s => `
      <li class="text-slate-300 flex items-center space-x-2">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        <span><strong class="text-white">[${escapeHtml(s.Project_Name)}]</strong> ${escapeHtml(s.Step_Name)}</span>
      </li>
    `).join('');
  }

  // Render Time Logs
  const timelogsListEl = document.getElementById('shift-timelogs-list');
  if (filteredTimeLogs.length === 0) {
    timelogsListEl.innerHTML = `<li class="text-slate-500 italic">No time logs to report for selected project(s).</li>`;
  } else {
    timelogsListEl.innerHTML = filteredTimeLogs.map(t => `
      <li class="text-slate-300 flex items-center justify-between">
        <span><strong class="text-white">[${escapeHtml(t.Project_Name)}]</strong> ${escapeHtml(t.Description || 'Work shift')}</span>
        <span class="font-mono text-sky-400 font-semibold">${t.Hours_Logged}h (${t.Start_Time} - ${t.End_Time})</span>
      </li>
    `).join('');
  }

  // Render Updates
  const updatesListEl = document.getElementById('shift-updates-list');
  if (filteredUpdates.length === 0) {
    updatesListEl.innerHTML = `<li class="text-slate-500 italic">No updates to report for selected project(s).</li>`;
  } else {
    updatesListEl.innerHTML = filteredUpdates.map(u => `
      <li class="text-slate-300">
        <strong class="text-white">[${escapeHtml(u.Project_Name)}]</strong> ${escapeHtml(u.Note_Text)}
      </li>
    `).join('');
  }

  // Render Attachments
  const attListEl = document.getElementById('shift-attachments-list');
  if (filteredAttachments.length === 0) {
    attListEl.innerHTML = `<li class="text-slate-500 italic">No files to attach for selected project(s).</li>`;
  } else {
    attListEl.innerHTML = filteredAttachments.map(a => `
      <li class="text-slate-300 flex items-center space-x-2">
        ${ICONS.paperclip}
        <span><strong class="text-white">[${escapeHtml(a.Project_Name)}]</strong> ${escapeHtml(a.File_Name)}</span>
      </li>
    `).join('');
  }

  // Update Trigger Button State & Text
  const triggerBtn = document.getElementById('btn-trigger-outlook');
  const labelEl = document.getElementById('trigger-outlook-label');
  if (selected.size === 0) {
    triggerBtn.disabled = true;
    labelEl.innerHTML = `Select at least 1 project`;
  } else if (selected.size === 1) {
    triggerBtn.disabled = false;
    labelEl.innerHTML = `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"></path>
      </svg>
      Preview Email for 1 Project
    `;
  } else {
    triggerBtn.disabled = false;
    labelEl.innerHTML = `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"></path>
      </svg>
      Preview Email for ${selected.size} Projects
    `;
  }
}

function closeShiftModal() {
  document.getElementById('modal-shift').classList.add('hidden');
}

async function triggerOutlookDraft() {
  const selectedIds = Array.from(state.shiftSelectedProjectIds);
  if (selectedIds.length === 0) {
    showToast('Please select at least one project for the report', 'error');
    return;
  }

  const triggerBtn = document.getElementById('btn-trigger-outlook');
  const labelEl = document.getElementById('trigger-outlook-label');
  const originalHtml = labelEl.innerHTML;

  triggerBtn.disabled = true;
  labelEl.innerHTML = `${ICONS.spinner} Launching...`;

  const activeUser = getActiveUser();
  const userId = activeUser ? activeUser.ID : null;
  const postPayload = { project_ids: selectedIds };
  if (userId) postPayload.user_id = userId;

  try {
    const res = await fetch('/api/end-of-shift', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(postPayload),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Failed to generate Outlook draft');
    }

    showToast('Classic Outlook draft generated! (Tip: If using New Outlook/Web, use "Copy Formatted Email" to paste)', 'success');
    closeShiftModal();

    // Reload active project and sidebar projects to reflect Reported_Flag = 1
    if (state.activeProjectId) {
      await selectProject(state.activeProjectId, false);
    }
    await loadProjects(false);

  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    triggerBtn.disabled = false;
    labelEl.innerHTML = originalHtml;
  }
}

async function copyFormattedEmail() {
  const selectedIds = Array.from(state.shiftSelectedProjectIds);
  if (selectedIds.length === 0) {
    showToast('Please select at least one project for the report', 'error');
    return;
  }

  const copyBtn = document.getElementById('btn-copy-shift-email');
  const labelEl = document.getElementById('copy-email-label');
  const originalHtml = labelEl.innerHTML;

  copyBtn.disabled = true;
  labelEl.innerHTML = `${ICONS.spinner} Copying...`;

  const activeUser = getActiveUser();
  const userId = activeUser ? activeUser.ID : null;
  let previewUrl = `/api/end-of-shift/preview?project_ids=${selectedIds.join(',')}`;
  if (userId) previewUrl += `&user_id=${userId}`;

  try {
    const res = await fetch(previewUrl);
    if (!res.ok) {
      throw new Error('Failed to render report HTML');
    }
    const htmlText = await res.text();

    // Generate plain-text representation fallback
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = htmlText;
    const plainText = tempDiv.innerText || tempDiv.textContent || '';

    // Modern Clipboard API with text/html blob
    let copySuccessful = false;
    if (navigator.clipboard && window.ClipboardItem) {
      try {
        const blobHtml = new Blob([htmlText], { type: 'text/html' });
        const blobText = new Blob([plainText], { type: 'text/plain' });
        await navigator.clipboard.write([
          new ClipboardItem({
            'text/html': blobHtml,
            'text/plain': blobText,
          }),
        ]);
        copySuccessful = true;
      } catch (clipErr) {
        console.warn('ClipboardItem write failed, trying fallback...', clipErr);
      }
    }

    if (!copySuccessful) {
      // Document copy fallback
      const copyHandler = (e) => {
        e.clipboardData.setData('text/html', htmlText);
        e.clipboardData.setData('text/plain', plainText);
        e.preventDefault();
      };
      document.addEventListener('copy', copyHandler);
      document.execCommand('copy');
      document.removeEventListener('copy', copyHandler);
    }

    // Mark included records as Reported_Flag = 1 in database
    const postPayload = { project_ids: selectedIds };
    if (userId) postPayload.user_id = userId;
    await fetch('/api/end-of-shift/mark-reported', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(postPayload),
    });

    showToast('Report copied! In your Outlook email draft, press Ctrl+V to paste.', 'success');
    closeShiftModal();

    if (state.activeProjectId) {
      await selectProject(state.activeProjectId, false);
    }
    await loadProjects(false);

  } catch (err) {
    showToast('Failed to copy formatted email: ' + err.message, 'error');
  } finally {
    copyBtn.disabled = false;
    labelEl.innerHTML = originalHtml;
  }
}

function downloadShiftEml() {
  const selectedIds = Array.from(state.shiftSelectedProjectIds);
  if (selectedIds.length === 0) {
    showToast('Please select at least one project to download', 'error');
    return;
  }
  const activeUser = getActiveUser();
  const userId = activeUser ? activeUser.ID : null;
  let emlUrl = `/api/end-of-shift/eml?project_ids=${selectedIds.join(',')}`;
  if (userId) emlUrl += `&user_id=${userId}`;
  window.location.href = emlUrl;
}

// ---------------------------------------------------------------------------
// GLOBAL EVENT LISTENERS BINDING
// ---------------------------------------------------------------------------
function initEventListeners() {
  // Hitlist search filter
  document.getElementById('search-projects-input').addEventListener('input', () => {
    filterProjects();
  });

  // Header status select change
  document.getElementById('proj-header-status-select').addEventListener('change', (e) => {
    updateProjectStatus(e.target.value);
  });

  // Save Project Metadata button
  document.getElementById('btn-save-project-notes').addEventListener('click', () => {
    saveProjectMetadata();
  });

  // Delete Project button
  document.getElementById('btn-delete-project').addEventListener('click', () => {
    if (state.activeProjectId && confirm(`Are you sure you want to delete "${state.activeProjectData.Name}"? This action cannot be undone.`)) {
      deleteProject(state.activeProjectId);
    }
  });

  // Post update button & enter key
  document.getElementById('btn-post-update').addEventListener('click', postUpdate);
  document.getElementById('new-update-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      postUpdate();
    }
  });

  // Real-time contact link updates on input
  const pmEmailInput = document.getElementById('edit-pm-email-input');
  const contractorPhoneInput = document.getElementById('edit-contractor-phone-input');
  if (pmEmailInput) {
    pmEmailInput.addEventListener('input', (e) => {
      updateContactLinks(state.activeProjectData?.Name, e.target.value, contractorPhoneInput ? contractorPhoneInput.value : '');
    });
  }
  if (contractorPhoneInput) {
    contractorPhoneInput.addEventListener('input', (e) => {
      updateContactLinks(state.activeProjectData?.Name, pmEmailInput ? pmEmailInput.value : '', e.target.value);
    });
  }

  // New Project Modal controls
  const newProjModal = document.getElementById('modal-new-project');
  const openNewProjModal = () => {
    document.getElementById('form-create-project').reset();
    newProjModal.classList.remove('hidden');
  };
  const closeNewProjModal = () => {
    newProjModal.classList.add('hidden');
  };

  document.getElementById('btn-open-new-project-modal').addEventListener('click', openNewProjModal);
  document.getElementById('btn-empty-new-project').addEventListener('click', openNewProjModal);
  document.getElementById('btn-close-new-project-modal').addEventListener('click', closeNewProjModal);
  document.getElementById('btn-cancel-create-project').addEventListener('click', closeNewProjModal);

  document.getElementById('form-create-project').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('new-proj-name').value.trim();
    const contractor = document.getElementById('new-proj-contractor').value.trim();
    const pmName = (document.getElementById('new-proj-pm-name')?.value || '').trim();
    const pmEmail = (document.getElementById('new-proj-pm-email')?.value || '').trim();
    const leadName = (document.getElementById('new-proj-contractor-lead')?.value || '').trim();
    const leadPhone = (document.getElementById('new-proj-contractor-phone')?.value || '').trim();
    const status = document.getElementById('new-proj-status').value;
    const notes = document.getElementById('new-proj-notes').value.trim();

    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          Name: name,
          Contractor_Name: contractor,
          Status: status,
          Notes: notes,
          Project_Manager_Name: pmName,
          Project_Manager_Email: pmEmail,
          Contractor_Lead_Name: leadName,
          Contractor_Lead_Phone: leadPhone,
        }),
      });
      if (!res.ok) throw new Error('Failed to create project');
      const data = await res.json();
      closeNewProjModal();
      showToast('Project created successfully');
      await loadProjects(false);
      selectProject(data.ID);
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Add Phase Modal controls
  const addPhaseModal = document.getElementById('modal-add-phase');
  const openAddPhaseModal = () => {
    document.getElementById('form-add-phase').reset();
    addPhaseModal.classList.remove('hidden');
  };
  const closeAddPhaseModal = () => {
    addPhaseModal.classList.add('hidden');
  };

  document.getElementById('btn-open-add-phase-modal').addEventListener('click', openAddPhaseModal);
  document.getElementById('btn-close-add-phase-modal').addEventListener('click', closeAddPhaseModal);
  document.getElementById('btn-cancel-add-phase').addEventListener('click', closeAddPhaseModal);

  document.getElementById('form-add-phase').addEventListener('submit', async (e) => {
    e.preventDefault();
    const phaseName = document.getElementById('new-phase-name-input').value.trim();
    const phaseNotes = (document.getElementById('new-phase-notes-input')?.value || '').trim();
    if (phaseName) {
      closeAddPhaseModal();
      await addPhase(phaseName, phaseNotes);
    }
  });

  // Step Details Pop-out Modal controls
  document.getElementById('btn-close-step-modal').addEventListener('click', closeStepDetailsModal);
  document.getElementById('btn-cancel-step-modal').addEventListener('click', closeStepDetailsModal);
  const stepDetailsModal = document.getElementById('modal-step-details');
  if (stepDetailsModal) {
    stepDetailsModal.addEventListener('click', (e) => {
      if (e.target === stepDetailsModal) {
        closeStepDetailsModal();
      }
    });
  }

  document.getElementById('form-edit-step-details').addEventListener('submit', async (e) => {
    e.preventDefault();
    const stepId = document.getElementById('modal-step-id').value;
    const stepName = document.getElementById('modal-step-name-input').value.trim();
    const details = document.getElementById('modal-step-details-textarea').value.trim();
    if (stepName) {
      closeStepDetailsModal();
      await updateStep(stepId, stepName, details);
    }
  });

  // Drag and Drop Zone for Attachments
  const dropZone = document.getElementById('drop-zone');
  const fileFallback = document.getElementById('file-input-fallback');
  const browseBtn = document.getElementById('btn-browse-files');

  browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileFallback.click();
  });

  dropZone.addEventListener('click', () => {
    fileFallback.click();
  });

  fileFallback.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      uploadFiles(e.target.files);
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('dragover-zone');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('dragover-zone');
    }, false);
  });

  dropZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      uploadFiles(files);
    }
  });

  // Time Tracking Form
  const timeForm = document.getElementById('form-log-time');
  const calcBtn = document.getElementById('btn-calc-hours');
  
  const autoCalculateHours = () => {
    const start = document.getElementById('timelog-start').value;
    const end = document.getElementById('timelog-end').value;
    if (start && end) {
      const [sH, sM] = start.split(':').map(Number);
      const [eH, eM] = end.split(':').map(Number);
      let diffMinutes = (eH * 60 + eM) - (sH * 60 + sM);
      if (diffMinutes < 0) diffMinutes += 24 * 60; // Overnight shift handle
      const rawHours = diffMinutes / 60;
      const hours = Math.round(rawHours * 100) / 100;
      document.getElementById('timelog-hours').value = hours;
    }
  };

  if (calcBtn) calcBtn.addEventListener('click', autoCalculateHours);
  const startInput = document.getElementById('timelog-start');
  const endInput = document.getElementById('timelog-end');
  if (startInput) startInput.addEventListener('change', autoCalculateHours);
  if (endInput) endInput.addEventListener('change', autoCalculateHours);

  timeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const start = document.getElementById('timelog-start').value;
    const end = document.getElementById('timelog-end').value;
    const hours = document.getElementById('timelog-hours').value;
    const desc = document.getElementById('timelog-desc').value.trim();

    await logTime(start, end, hours, desc);
    timeForm.reset();
  });

  // Shift Report Triggers
  const btnHeaderShift = document.getElementById('btn-header-shift');
  if (btnHeaderShift) btnHeaderShift.addEventListener('click', openShiftModal);

  const btnCloseShift = document.getElementById('btn-close-shift-modal');
  if (btnCloseShift) btnCloseShift.addEventListener('click', closeShiftModal);

  const btnCancelShift = document.getElementById('btn-cancel-shift');
  if (btnCancelShift) btnCancelShift.addEventListener('click', closeShiftModal);

  const btnTriggerOutlook = document.getElementById('btn-trigger-outlook');
  if (btnTriggerOutlook) btnTriggerOutlook.addEventListener('click', triggerOutlookDraft);

  const btnCopyShiftEmail = document.getElementById('btn-copy-shift-email');
  if (btnCopyShiftEmail) btnCopyShiftEmail.addEventListener('click', copyFormattedEmail);

  const btnDownloadEml = document.getElementById('btn-download-eml');
  if (btnDownloadEml) btnDownloadEml.addEventListener('click', downloadShiftEml);

  const btnPreviewShift = document.getElementById('btn-preview-shift');
  if (btnPreviewShift) {
    btnPreviewShift.addEventListener('click', () => {
      const selectedIds = Array.from(state.shiftSelectedProjectIds);
      if (selectedIds.length === 0) {
        showToast('Please select at least one project to preview', 'error');
        return;
      }
      const activeUser = getActiveUser();
      const userId = activeUser ? activeUser.ID : null;
      let previewUrl = `/api/end-of-shift/preview?project_ids=${selectedIds.join(',')}`;
      if (userId) previewUrl += `&user_id=${userId}`;
      window.open(previewUrl, '_blank');
    });
  }

  // Shift Modal Project Quick Selection Buttons
  const btnSelectAll = document.getElementById('btn-shift-select-all');
  if (btnSelectAll) {
    btnSelectAll.addEventListener('click', () => {
      if (state.shiftSummaryData && state.shiftSummaryData.projects_overview) {
        state.shiftSelectedProjectIds = new Set(state.shiftSummaryData.projects_overview.map(p => p.ID));
        document.querySelectorAll('.shift-proj-checkbox').forEach(chk => { chk.checked = true; });
        updateShiftModalFilteredView();
      }
    });
  }

  const btnSelectActive = document.getElementById('btn-shift-select-active');
  if (btnSelectActive) {
    btnSelectActive.addEventListener('click', () => {
      if (state.shiftSummaryData && state.shiftSummaryData.projects_overview) {
        if (state.activeProjectId && state.shiftSummaryData.projects_overview.some(p => p.ID === state.activeProjectId)) {
          state.shiftSelectedProjectIds = new Set([state.activeProjectId]);
        } else if (state.shiftSummaryData.projects_overview.length > 0) {
          state.shiftSelectedProjectIds = new Set([state.shiftSummaryData.projects_overview[0].ID]);
        }
        document.querySelectorAll('.shift-proj-checkbox').forEach(chk => {
          const pid = parseInt(chk.getAttribute('data-project-id'), 10);
          chk.checked = state.shiftSelectedProjectIds.has(pid);
        });
        updateShiftModalFilteredView();
      }
    });
  }

  // Custom User Selector Dropdown interactions
  const btnUserDropdownToggle = document.getElementById('btn-user-dropdown-toggle');
  const userDropdownMenu = document.getElementById('user-dropdown-menu');
  const userChevron = document.getElementById('header-user-chevron');
  const userContainer = document.getElementById('user-selector-container');

  if (btnUserDropdownToggle && userDropdownMenu) {
    btnUserDropdownToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const isHidden = userDropdownMenu.classList.contains('hidden');
      if (isHidden) {
        userDropdownMenu.classList.remove('hidden');
        if (userChevron) userChevron.classList.add('rotate-180');
      } else {
        userDropdownMenu.classList.add('hidden');
        if (userChevron) userChevron.classList.remove('rotate-180');
      }
    });

    document.addEventListener('click', (e) => {
      if (userContainer && !userContainer.contains(e.target)) {
        userDropdownMenu.classList.add('hidden');
        if (userChevron) userChevron.classList.remove('rotate-180');
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !userDropdownMenu.classList.contains('hidden')) {
        userDropdownMenu.classList.add('hidden');
        if (userChevron) userChevron.classList.remove('rotate-180');
      }
    });
  }

  const btnDropdownManageTeam = document.getElementById('btn-dropdown-manage-team');
  if (btnDropdownManageTeam) {
    btnDropdownManageTeam.addEventListener('click', () => {
      if (userDropdownMenu) userDropdownMenu.classList.add('hidden');
      if (userChevron) userChevron.classList.remove('rotate-180');
      openSettingsModal();
    });
  }

  // Legacy / hidden select fallback listener
  const userSelect = document.getElementById('select-active-user');
  if (userSelect) {
    userSelect.addEventListener('change', (e) => {
      setActiveUser(e.target.value);
    });
  }

  // Settings Modal Triggers
  const btnOpenSettings = document.getElementById('btn-open-settings-modal');
  if (btnOpenSettings) btnOpenSettings.addEventListener('click', openSettingsModal);

  const btnCloseSettings = document.getElementById('btn-close-settings-modal');
  if (btnCloseSettings) btnCloseSettings.addEventListener('click', closeSettingsModal);

  const btnCloseSettingsFooter = document.getElementById('btn-close-settings-footer');
  if (btnCloseSettingsFooter) btnCloseSettingsFooter.addEventListener('click', closeSettingsModal);

  // Add User Form
  const formAddUser = document.getElementById('form-add-user');
  if (formAddUser) {
    formAddUser.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('new-user-name').value.trim();
      const role = document.getElementById('new-user-role').value.trim();
      const email = document.getElementById('new-user-email').value.trim();
      if (!name) return;
      await createUser(name, email, role);
      formAddUser.reset();
    });
  }
}

// ---------------------------------------------------------------------------
// USER / TEAM MANAGEMENT CONTROLLER
// ---------------------------------------------------------------------------
async function loadUsers() {
  try {
    const res = await fetch('/api/users');
    if (!res.ok) throw new Error('Failed to load team members');
    const users = await res.json();
    state.users = users;

    const savedUserId = localStorage.getItem('hitachi_active_user_id');
    if (savedUserId && state.users.some(u => u.ID === parseInt(savedUserId, 10))) {
      state.activeUserId = parseInt(savedUserId, 10);
    } else if (state.users.length > 0) {
      state.activeUserId = state.users[0].ID;
      localStorage.setItem('hitachi_active_user_id', state.activeUserId);
    } else {
      state.activeUserId = null;
    }

    renderHeaderUserSelector();
    updateTeamBadge();
  } catch (err) {
    console.error('Error loading users:', err);
  }
}

function getActiveUser() {
  if (!state.users || state.users.length === 0) return null;
  return state.users.find(u => u.ID === state.activeUserId) || state.users[0] || null;
}

function setActiveUser(userId) {
  const parsedId = parseInt(userId, 10);
  const found = state.users.find(u => u.ID === parsedId);
  if (!found) return;

  state.activeUserId = parsedId;
  localStorage.setItem('hitachi_active_user_id', parsedId);
  renderHeaderUserSelector();

  const reportingBadge = document.getElementById('shift-reporting-user-badge');
  if (reportingBadge) {
    reportingBadge.textContent = `${found.Name} (${found.Role || 'Technician'})`;
  }

  showToast(`Active profile switched to ${found.Name}`, 'info');
}

function renderHeaderUserSelector() {
  const avatarEl = document.getElementById('header-user-avatar');
  const nameEl = document.getElementById('header-user-name');
  const listEl = document.getElementById('user-dropdown-list');
  const selectEl = document.getElementById('select-active-user');

  const activeUser = getActiveUser();

  // Update Trigger Button
  if (avatarEl) {
    avatarEl.textContent = activeUser ? (activeUser.Name.trim().charAt(0).toUpperCase() || 'U') : 'U';
  }
  if (nameEl) {
    if (activeUser) {
      nameEl.textContent = `${activeUser.Name} (${activeUser.Role || 'Field Tech'})`;
    } else {
      nameEl.textContent = 'Select User';
    }
  }

  // Update Custom Floating High-Contrast Dropdown List
  if (listEl) {
    if (!state.users || state.users.length === 0) {
      listEl.innerHTML = `<div class="px-3 py-2 text-xs text-slate-400">No active team members</div>`;
    } else {
      listEl.innerHTML = state.users.map(u => {
        const isActive = u.ID === state.activeUserId;
        const initial = (u.Name && u.Name.trim().length > 0) ? u.Name.trim().charAt(0).toUpperCase() : 'U';
        return `
          <button type="button" class="w-full flex items-center gap-2.5 px-3 py-2 text-left transition hover:bg-slate-800/90 cursor-pointer ${isActive ? 'bg-indigo-950/60' : ''}" data-user-id="${u.ID}">
            <div class="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 font-semibold text-xs flex items-center justify-center shrink-0">
              ${initial}
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-semibold ${isActive ? 'text-indigo-200' : 'text-slate-100'} truncate">
                ${escapeHtml(u.Name)}
              </div>
              <div class="text-[10px] text-slate-400 truncate">
                ${escapeHtml(u.Role || 'Field Tech')}
              </div>
            </div>
            ${isActive ? `
              <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            ` : ''}
          </button>
        `;
      }).join('');

      // Attach click events to each user item
      listEl.querySelectorAll('button[data-user-id]').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const uid = parseInt(btn.getAttribute('data-user-id'), 10);
          setActiveUser(uid);
          const menu = document.getElementById('user-dropdown-menu');
          const chevron = document.getElementById('header-user-chevron');
          if (menu) menu.classList.add('hidden');
          if (chevron) chevron.classList.remove('rotate-180');
        });
      });
    }
  }

  // Sync hidden native select for backwards compatibility
  if (selectEl) {
    selectEl.innerHTML = (state.users || []).map(u => `
      <option value="${u.ID}" ${u.ID === state.activeUserId ? 'selected' : ''}>
        ${escapeHtml(u.Name)} (${escapeHtml(u.Role || 'Tech')})
      </option>
    `).join('');
  }
}

function updateTeamBadge() {
  const badgeEl = document.getElementById('settings-team-count-badge');
  if (badgeEl) {
    const count = state.users.length;
    badgeEl.textContent = `${count} ${count === 1 ? 'member' : 'members'}`;
  }
}

function openSettingsModal() {
  const modal = document.getElementById('modal-settings');
  if (modal) {
    modal.classList.remove('hidden');
    renderSettingsUsersList();
  }
}

function closeSettingsModal() {
  const modal = document.getElementById('modal-settings');
  if (modal) modal.classList.add('hidden');
}

function renderSettingsUsersList() {
  const container = document.getElementById('settings-users-list');
  const countEl = document.getElementById('settings-users-count');
  if (!container) return;

  if (countEl) countEl.textContent = `${state.users.length} active`;

  if (state.users.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 italic p-3 text-center">No team members found.</div>`;
    return;
  }

  container.innerHTML = state.users.map(u => {
    const isActive = u.ID === state.activeUserId;
    const initial = (u.Name || 'U').charAt(0).toUpperCase();
    const canDelete = state.users.length > 1;

    return `
      <div class="flex items-center justify-between p-3 rounded-lg bg-slate-950/70 border ${isActive ? 'border-indigo-500/50 ring-1 ring-indigo-500/20' : 'border-slate-800'} transition">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-8 h-8 rounded-full ${isActive ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/30' : 'bg-slate-800 text-slate-300'} font-semibold text-xs flex items-center justify-center shrink-0">
            ${initial}
          </div>
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-slate-200 truncate">${escapeHtml(u.Name)}</span>
              ${isActive ? '<span class="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Active</span>' : ''}
              <span class="text-[11px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-medium">${escapeHtml(u.Role || 'Technician')}</span>
            </div>
            ${u.Email ? `<div class="text-xs text-slate-400 truncate mt-0.5">${escapeHtml(u.Email)}</div>` : '<div class="text-xs text-slate-600 truncate mt-0.5">No email provided</div>'}
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          ${!isActive ? `
            <button data-user-id="${u.ID}" class="btn-set-active-user px-2.5 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition-colors">
              Select
            </button>
          ` : ''}
          ${canDelete ? `
            <button data-user-id="${u.ID}" data-user-name="${escapeHtml(u.Name)}" title="Remove team member" class="btn-delete-user p-1.5 rounded text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors">
              ${ICONS.trash}
            </button>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');

  // Attach button listeners
  container.querySelectorAll('.btn-set-active-user').forEach(btn => {
    btn.addEventListener('click', () => {
      const uid = btn.getAttribute('data-user-id');
      setActiveUser(uid);
      renderSettingsUsersList();
    });
  });

  container.querySelectorAll('.btn-delete-user').forEach(btn => {
    btn.addEventListener('click', async () => {
      const uid = btn.getAttribute('data-user-id');
      const uName = btn.getAttribute('data-user-name');
      if (confirm(`Remove "${uName}" from active team members?`)) {
        await deleteUser(uid);
      }
    });
  });
}

async function createUser(name, email, role) {
  try {
    const res = await fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ Name: name, Email: email, Role: role }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to add team member');

    showToast(`Added ${data.Name} to team`, 'success');
    await loadUsers();
    setActiveUser(data.ID);
    renderSettingsUsersList();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteUser(userId) {
  try {
    const res = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to remove team member');

    showToast('Team member removed');
    await loadUsers();
    renderSettingsUsersList();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ---------------------------------------------------------------------------
// UTILITY HELPERS
// ---------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
