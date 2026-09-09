(function () {
  var caseAnimState = {};
  var currentUser = null;

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  async function api(path, options) {
    var res = await fetch(path, options);
    var body = await res.json().catch(function () { return null; });
    if (!res.ok) {
      var message = (body && body.error) || ("Request failed (" + res.status + ")");
      throw new Error(message);
    }
    return body;
  }

  function renderAuthWidget() {
    var el = document.getElementById("auth-widget");
    if (!el) return;
    if (currentUser) {
      el.innerHTML = '<span>Signed in as ' + escapeHtml(currentUser.name) + '</span><button type="button" id="logout-btn">Log out</button>';
      document.getElementById("logout-btn").addEventListener("click", function () {
        api("/api/logout", { method: "POST" }).then(function () {
          currentUser = null;
          renderAuthWidget();
          document.dispatchEvent(new CustomEvent("accord-auth-changed", { detail: null }));
        }).catch(function (err) {
          alert(err.message);
        });
      });
      return;
    }

    el.innerHTML = '<button type="button" id="open-auth">Log in / Register</button>';
    document.getElementById("open-auth").addEventListener("click", function () {
      document.getElementById("auth-panel").hidden = false;
    });
  }

  function switchAuthTab(tab) {
    document.querySelectorAll(".auth-tab").forEach(function (button) {
      button.classList.toggle("active", button.getAttribute("data-tab") === tab);
    });
    document.getElementById("login-form").hidden = tab !== "login";
    document.getElementById("register-form").hidden = tab !== "register";
  }

  function closeAuthPanel() {
    document.getElementById("auth-panel").hidden = true;
  }

  document.getElementById("auth-close").addEventListener("click", function () {
    document.getElementById("auth-panel").hidden = true;
  });
  document.getElementById("auth-panel").addEventListener("click", function (e) {
    if (e.target.id === "auth-panel") document.getElementById("auth-panel").hidden = true;
  });

  function handleAuthSubmit(formId, endpoint, errorId, fields) {
    document.getElementById(formId).addEventListener("submit", function (e) {
      e.preventDefault();
      var errorEl = document.getElementById(errorId);
      errorEl.classList.remove("visible");
      var payload = {};
      fields.forEach(function (f) {
        var el = document.getElementById(f.inputId);
        payload[f.name] = el.value.trim();
      });

      api(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (user) {
        currentUser = user;
        document.getElementById("auth-panel").hidden = true;
        e.target.reset();
        renderAuthWidget();
        document.dispatchEvent(new CustomEvent("accord-auth-changed", { detail: user }));
      }).catch(function (err) {
        errorEl.textContent = err.message;
        errorEl.classList.add("visible");
      });
    });
  }

  document.querySelectorAll(".auth-tab").forEach(function (button) {
    button.addEventListener("click", function () {
      switchAuthTab(button.getAttribute("data-tab"));
    });
  });

  document.getElementById("auth-close").addEventListener("click", closeAuthPanel);
  document.getElementById("auth-panel").addEventListener("click", function (event) {
    if (event.target.id === "auth-panel") closeAuthPanel();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeAuthPanel();
  });

  handleAuthSubmit("login-form", "/api/login", "login-error", [
    { name: "email", inputId: "login-email" },
    { name: "password", inputId: "login-password" }
  ]);
  handleAuthSubmit("register-form", "/api/register", "register-error", [
    { name: "name", inputId: "register-name" },
    { name: "email", inputId: "register-email" },
    { name: "password", inputId: "register-password" }
  ]);

  function renderRoles(roles) {
    var el = document.getElementById("role-list");
    if (roles.length === 0) { el.innerHTML = '<p class="empty-note">No roles posted yet.</p>'; return; }
    el.innerHTML = roles.map(function (r) {
      return '<div class="listing"><h3>' + escapeHtml(r.title) + '</h3>' +
        (r.description ? '<p>' + escapeHtml(r.description) + '</p>' : '') +
        '<div class="tags">' + r.skills.map(function (s) { return '<span class="tag">' + escapeHtml(s) + '</span>'; }).join('') + '</div>' +
        '<div class="meta">' + r.pay + ' USDC / month</div></div>';
    }).join('');
  }

  function renderProfiles(profiles) {
    var el = document.getElementById("profile-list");
    if (profiles.length === 0) { el.innerHTML = '<p class="empty-note">No profiles yet.</p>'; return; }
    el.innerHTML = profiles.map(function (p) {
      return '<div class="listing"><h3>' + escapeHtml(p.name) + '</h3>' +
        '<div class="tags">' + p.skills.map(function (s) { return '<span class="tag">' + escapeHtml(s) + '</span>'; }).join('') + '</div>' +
        '<div class="meta">Expects ' + p.rate + ' USDC / month' + (p.resume ? ' · <a href="' + escapeHtml(p.resume) + '" target="_blank" rel="noopener">résumé</a>' : '') + '</div></div>';
    }).join('');
  }

  function renderMatches(matches) {
    var el = document.getElementById("match-list");
    if (matches.length === 0) {
      el.innerHTML = '<p class="empty-note">No overlapping skills yet — post a role and a profile with at least one matching skill.</p>';
      return;
    }

    el.innerHTML = matches.map(function (m) {
      var key = m.role.id + "-" + m.profile.id;
      var anim = caseAnimState[key];
      var stage = anim ? anim.stage : (m.dispute ? 3 : 0);
      var verdict = anim && anim.verdict != null ? anim.verdict : (m.dispute ? m.dispute.verdict : null);
      var termsHtml = '<div class="terms-line"><span class="terms-figures">Role offers ' + m.role.pay + ' USDC · candidate expects ' + m.profile.rate + ' USDC</span>';

      if (!m.terms_differ) {
        termsHtml += '<span class="status-tag aligned">Terms aligned</span>';
      } else if (stage === 0) {
        termsHtml += '<span class="status-tag differ">Terms differ</span><button class="btn seal ghost" data-dispute="' + key + '" data-role="' + m.role.id + '" data-profile="' + m.profile.id + '">Raise a dispute</button>';
      } else if (stage < 3) {
        termsHtml += '<span class="status-tag differ">Case open</span>';
      } else {
        termsHtml += '<span class="status-tag aligned">Resolved</span>';
      }
      termsHtml += '</div>';

      var casePanel = '';
      if (stage > 0) {
        casePanel = '<div class="case-panel" aria-live="polite"><div class="case-id">Case ' + key.toUpperCase() + ' · GenLayer Internet Court</div>' +
          '<div class="case-step' + (stage >= 1 ? ' active' : '') + '">1. Case filed with the disputed term on record</div>' +
          '<div class="case-step' + (stage >= 2 ? ' active' : '') + '">2. A panel of validators is reviewing both positions</div>' +
          '<div class="case-step' + (stage >= 3 ? ' active' : '') + '">3. Verdict returned</div>';
        if (stage >= 3 && verdict != null) {
          casePanel += '<div class="verdict">Settled at <b>' + verdict + ' USDC / month</b> — the panel\'s ruling, stored on the server.</div>';
        }
        casePanel += '</div>';
      }

      return '<div class="match-row">' +
        '<div class="match-top"><div class="match-parties">' + escapeHtml(m.role.title) + '<span class="sep">×</span>' + escapeHtml(m.profile.name) + '</div>' +
        '<span class="overlap-pill">' + m.overlap_pct + '% skill overlap</span></div>' +
        '<div class="shared-skills">Shared skills: ' + (m.shared_skills.length ? m.shared_skills.join(', ') : 'none') + '</div>' +
        termsHtml + casePanel +
        '</div>';
    }).join('');

    document.querySelectorAll('[data-dispute]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        runDispute(btn.getAttribute('data-dispute'), btn.getAttribute('data-role'), btn.getAttribute('data-profile'));
      });
    });
  }

  async function refreshAll() {
    var results = await Promise.all([
      api("/api/roles"), api("/api/profiles"), api("/api/matches")
    ]);
    renderRoles(results[0]);
    renderProfiles(results[1]);
    renderMatches(results[2]);
    populateDisputeSelectors(results[0], results[1]);
  }

  function populateDisputeSelectors(roles, profiles) {
    var roleSelect = document.getElementById("dispute-role-select");
    var profileSelect = document.getElementById("dispute-profile-select");
    if (!roleSelect || !profileSelect) return;

    var previousRole = roleSelect.value;
    var previousProfile = profileSelect.value;
    roleSelect.innerHTML = roles.length
      ? roles.map(function (role) {
        return '<option value="' + role.id + '">' + escapeHtml(role.title) + ' (' + role.pay + ' USDC)</option>';
      }).join("")
      : '<option value="">No roles posted yet</option>';
    profileSelect.innerHTML = profiles.length
      ? profiles.map(function (profile) {
        return '<option value="' + profile.id + '">' + escapeHtml(profile.name) + ' (' + profile.rate + ' USDC)</option>';
      }).join("")
      : '<option value="">No profiles yet</option>';

    if (previousRole) roleSelect.value = previousRole;
    if (previousProfile) profileSelect.value = previousProfile;
  }

  function runDispute(key, roleId, profileId) {
    caseAnimState[key] = { stage: 1, verdict: null };
    refreshAll();
    setTimeout(function () {
      caseAnimState[key] = { stage: 2, verdict: null };
      refreshAll();
      api("/api/disputes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role_id: Number(roleId), profile_id: Number(profileId) })
      }).then(function (dispute) {
        setTimeout(function () {
          caseAnimState[key] = { stage: 3, verdict: dispute.verdict };
          refreshAll();
        }, 700);
      }).catch(function (err) {
        caseAnimState[key] = null;
        alert("Could not file the dispute: " + err.message);
        refreshAll();
      });
    }, 900);
  }

  document.getElementById("dispute-button").addEventListener("click", function () {
    var button = document.getElementById("dispute-button");
    var statusEl = document.getElementById("manual-dispute-status");
    var roleId = document.getElementById("dispute-role-select").value;
    var profileId = document.getElementById("dispute-profile-select").value;
    var reason = document.getElementById("dispute-reason").value.trim() || "Salary mismatch";

    if (!roleId || !profileId) {
      statusEl.innerHTML = '<p class="form-error visible">Post at least one role and one profile first.</p>';
      return;
    }

    button.disabled = true;
    statusEl.innerHTML = '<div class="case-panel" aria-live="polite">' +
      '<div class="case-id">Case ' + roleId + '-' + profileId + ' · GenLayer Internet Court</div>' +
      '<div class="case-step active">Filed — waiting for the dispute response.</div></div>';

    api("/api/disputes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role_id: Number(roleId),
        profile_id: Number(profileId),
        reason: reason
      })
    }).then(function (dispute) {
      statusEl.innerHTML = '<div class="case-panel" aria-live="polite">' +
        '<div class="case-id">Case ' + roleId + '-' + profileId + ' · GenLayer Internet Court</div>' +
        '<div class="case-step active">Verdict returned</div>' +
        '<div class="verdict">Settled at <b>' + escapeHtml(String(dispute.verdict)) + '</b> — the ruling is stored on the server.</div></div>';
      return refreshAll();
    }).catch(function (error) {
      statusEl.innerHTML = '<p class="form-error visible">' + escapeHtml(error.message) + '</p>';
    }).finally(function () {
      button.disabled = false;
    });
  });

  document.getElementById("role-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var errorEl = document.getElementById("role-error");
    errorEl.classList.remove("visible");
    api("/api/roles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: document.getElementById("role-title").value.trim(),
        description: document.getElementById("role-desc").value.trim(),
        skills: document.getElementById("role-skills").value,
        pay: document.getElementById("role-pay").value
      })
    }).then(function () {
      e.target.reset();
      return refreshAll();
    }).catch(function (err) {
      errorEl.textContent = err.message;
      errorEl.classList.add("visible");
    });
  });

  document.getElementById("profile-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var errorEl = document.getElementById("profile-error");
    errorEl.classList.remove("visible");
    api("/api/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("profile-name").value.trim(),
        resume: document.getElementById("profile-resume").value.trim(),
        skills: document.getElementById("profile-skills").value,
        rate: document.getElementById("profile-rate").value
      })
    }).then(function () {
      e.target.reset();
      return refreshAll();
    }).catch(function (err) {
      errorEl.textContent = err.message;
      errorEl.classList.add("visible");
    });
  });

  api("/api/me").then(function (user) {
    currentUser = user;
    renderAuthWidget();
  }).catch(function () {
    renderAuthWidget();
  });

  refreshAll().catch(function (err) {
    document.getElementById("match-list").innerHTML = '<p class="empty-note">Could not reach the API: ' + escapeHtml(err.message) + '</p>';
  });
})();
