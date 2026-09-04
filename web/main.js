   
    // ─── CONFIG (matches docker-compose ports) ───
    const CFG = {
      AUTH: 'http://localhost:8000',
      ORDER: 'http://localhost:8001',
      WS: 'ws://localhost:8003/ws/notifications',
    };

    // ─── STATE ───
    const S = {
      token: null, userId: null, username: null, role: null,
      loginRole: 'CLIENT',
      orders: [],      // both client & driver use same list
      ws: null,
      podId: null, failId: null,
      notifCount: 0,
      sigDown: false, sigHasContent: false,
    };

     //redirect to main app if logged in
    if(localStorage.getItem('jwt_token') && localStorage.getItem('username')) {
      S.token = localStorage.getItem('jwt_token');
      S.username = localStorage.getItem('username');
      S.userId = localStorage.getItem('userId');
      S.role = localStorage.getItem('role');
      console.log("Found existing token for user:", S.username);
      enterApp();
    }


    // ─── TOAST ───
    function toast(msg, type = 'info', ms = 3500) {
      const icons = { success: '✓', error: '✕', info: 'ℹ' };
      const el = document.createElement('div');
      el.className = `toast ${type}`;
      el.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
      document.getElementById('toast-container').appendChild(el);
      setTimeout(() => el.remove(), ms);
    }

    // ─── HTTP ───
    async function req(base, path, method = 'GET', body = null, auth = true) {
      const h = { 'Content-Type': 'application/json' };
      if (auth && S.token) h['Authorization'] = `Bearer ${S.token}`;
      const opts = { method, headers: h };
      if (body) opts.body = JSON.stringify(body);
      const res = await fetch(base + path, opts);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
      return data;
    }

    // ─── SCREEN / MODAL ───
    function show(id) {
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.getElementById(id).classList.add('active');
    }
    function openModal(id) { document.getElementById(id).classList.add('open'); }
    function closeModal(id) { document.getElementById(id).classList.remove('open'); }

    // ─── LOGIN ROLE ───
    function setLoginRole(role) {
      S.loginRole = role;
      ['CLIENT', 'DRIVER'].forEach(r => document.getElementById('rtab-' + r).classList.toggle('active', r === role));
    }

    // ─── REGISTER ───
    async function doRegister() {
      const btn = document.getElementById('reg-btn');
      const username = v('r-user'), email = v('r-email'), password = v('r-pass'), role = v('r-role');
      if (!username || !email || !password) { toast('Fill all fields', 'error'); return; }
      setBtn(btn, true, 'Creating…');
      try {
        await req(CFG.AUTH, '/auth/register', 'POST', { username, email, password, role }, false);
        toast(`Account created! Sign in as ${username}`, 'success');
        closeModal('reg-modal');
        document.getElementById('l-user').value = username;
        setLoginRole(role);
      } catch (e) { toast(e.message, 'error'); }
      finally { setBtn(btn, false, 'Create Account'); }
    }

    // ─── LOGIN ───
    async function doLogin() {
      const btn = document.getElementById('login-btn');
      const username = v('l-user'), password = v('l-pass');
      if (!username || !password) { toast('Enter credentials', 'error'); return; }
      setBtn(btn, true, 'Signing in…');
      try {
        const data = await req(CFG.AUTH, '/auth/login', 'POST', { username, password }, false);
        S.token = data.access_token;
        S.username = username;
        const p = JSON.parse(atob(S.token.split('.')[1]));
        S.userId = p.sub;
        S.role = p.role;
        localStorage.setItem('jwt_token', S.token);
        localStorage.setItem('username', username);
        localStorage.setItem('role', S.role);
        localStorage.setItem('userId', S.userId);
        enterApp();
      } catch (e) { toast(e.message || 'Login failed', 'error'); }
      finally { setBtn(btn, false, 'Sign In'); }
    }

    // ─── ENTER APP ───
    function enterApp() {
      const badge = document.getElementById('nav-badge');
      badge.textContent = S.role;
      badge.className = `nav-badge badge-${S.role}`;
      const av = document.getElementById('nav-av');
      av.textContent = S.username[0].toUpperCase();
      av.className = `nav-av av-${S.role}`;
      document.getElementById('nav-username').textContent = S.username;

      document.getElementById('client-view').classList.toggle('hide', S.role !== 'CLIENT');
      document.getElementById('driver-view').classList.toggle('hide', S.role !== 'DRIVER');

      show('app-screen');
      connectWS();
      if (S.role === 'CLIENT' || S.role === 'DRIVER') loadOrders();
    }

    // ─── LOGOUT ───
    function doLogout() {
      if (S.ws) { S.ws.close(); S.ws = null; }
      Object.assign(S, { token: null, userId: null, username: null, role: null, orders: [], notifCount: 0 });
      localStorage.removeItem('jwt_token');
      localStorage.removeItem('username');
      localStorage.removeItem('role');
      localStorage.removeItem('userId');
      // Reset UI
      document.getElementById('orders-body').innerHTML = '<tr><td colspan="5"><div class="empty"><div class="empty-icon">📦</div>Loading…</div></td></tr>';
      document.getElementById('client-notifs').innerHTML = '<div class="notif-empty">Events from the order pipeline will appear here in real-time via WebSocket.</div>';
      document.getElementById('drv-notifs').innerHTML = '<div class="notif-empty" style="font-size:12px">No events yet.</div>';
      document.getElementById('drv-alerts').innerHTML = '<div class="notif-empty" style="font-size:12px">Real-time route &amp; priority alerts appear here.</div>';
      show('login-screen');
    }

    // ─── WEBSOCKET ───
    function connectWS() {
      const dot = document.getElementById('ws-dot');
      const lbl = document.getElementById('ws-status');
      try {
        S.ws = new WebSocket(CFG.WS);
        S.ws.onopen = () => {
          dot.classList.add('on');
          if (lbl) lbl.textContent = 'Connected — live updates active';
        };
        S.ws.onmessage = (e) => {
          try { onWSEvent(JSON.parse(e.data)); } catch { }
        };
        S.ws.onclose = () => {
          dot.classList.remove('on');
          if (lbl) lbl.textContent = 'Reconnecting…';
          setTimeout(connectWS, 3000);
        };
        S.ws.onerror = () => {
          dot.classList.remove('on');
          if (lbl) lbl.textContent = 'Connection error';
        };
      } catch { if (lbl) lbl.textContent = 'WebSocket unavailable'; }
    }

    function onWSEvent(evt) {
      const key = evt.event || '';
      const data = evt.data || {};
      const oid = data.order_id || '';
      const time = new Date().toLocaleTimeString();

      const labels = {
        'order.created': '📦 Order created',
        'cms.confirmed': '📋 CMS confirmed order',
        'wms.registered': '🏭 Package registered at warehouse',
        'ros.route_assigned': '🛣️ Route assigned — out for delivery',
        'order.delivered': '✅ Order delivered',
        'order.failed': '❌ Order failed',
        'order.compensate': '↩️ Saga compensation triggered',
        'ros.driver_unavailable': '⚠️ Driver unavailable — Route reassignment in progress',
      };
      const label = labels[key] || key;
      const short = `${oid ? `<strong>${oid.substring(0, 8)}…</strong> — ` : ''}${label}`;

      // Append to client notifications
      const cn = document.getElementById('client-notifs');
      removeEmpty(cn);
      const ni = makeNotif(short, time);
      cn.prepend(ni);

      // Append to driver notifications
      const dn = document.getElementById('drv-notifs');
      removeEmpty(dn);
      dn.prepend(makeNotif(short, time, true));
      while (dn.children.length > 12) dn.lastChild.remove();

      // Driver alert for route_assigned
      if (key === 'ros.route_assigned') {
        const da = document.getElementById('drv-alerts');
        removeEmpty(da);
        const al = document.createElement('div');
        al.className = 'alert alert-warn';
        al.innerHTML = `<span>⚡</span><span>Route assigned for <strong>${oid.substring(0, 8)}…</strong> — Driver: ${data.driver_id || 'N/A'}</span>`;
        da.prepend(al);

        // Auto-load the order for driver
        if (S.role === 'DRIVER' && oid) {
          req(CFG.ORDER, `/api/v1/orders/${oid}`)
            .then(o => { upsertOrder(o); renderDriver(); })
            .catch(() => { });
        }
      }

      if (key === 'order.delivered' || key === 'order.failed') {
        // Refresh that order's status
        if (oid) {
          req(CFG.ORDER, `/api/v1/orders/${oid}`)
            .then(o => { upsertOrder(o); renderOrders(); renderDriver(); updateClientStats(); updateDriverStats(); })
            .catch(() => { });
        }
      }

      // Badge
      S.notifCount++;
      const nb = document.getElementById('notif-badge');
      if (nb) { nb.textContent = S.notifCount; nb.style.display = 'inline'; }

      const toastType = key === 'order.delivered' ? 'success' : key.includes('fail') ? 'error' : 'info';
      toast(short.replace(/<[^>]+>/g, ''), toastType);
      loadOrders();
    }

    function makeNotif(html, time, small = false) {
      const d = document.createElement('div');
      d.className = 'notif-item';
      if (small) d.style.fontSize = '12px';
      d.innerHTML = `${html}<div class="notif-time">${time}</div>`;
      return d;
    }
    function removeEmpty(el) {
      const e = el.querySelector('.notif-empty');
      if (e) e.remove();
    }

    // ─── CLIENT TABS ───
    function cTab(name, btn) {
      document.querySelectorAll('#client-view .tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('#client-view .tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tp-' + name).classList.add('active');
      if (name === 'notifs') {
        S.notifCount = 0;
        const nb = document.getElementById('notif-badge');
        if (nb) nb.style.display = 'none';
      }
    }

    // ─── LOAD ORDERS ───
    async function loadOrders() {
      if(S.role === 'DRIVER') {
        const orderData = await req(CFG.ORDER, '/api/v1/drivers/'+S.userId+'/deliveries');
        S.orders = orderData;
        renderDriver();
      } else if(S.role === 'CLIENT') {
        const orderData = await req(CFG.ORDER, '/api/v1/orders/my-orders/'+S.userId);
        S.orders = orderData;
        renderOrders();
      }
      updateClientStats();
    }

    function upsertOrder(o) {
      const idx = S.orders.findIndex(x => x.id === o.id);
      if (idx === -1) S.orders.unshift(o);
      else S.orders[idx] = o;
    }

    const STATUS_LABEL = {
      CREATED: 'Created', CMS_CONFIRMED: 'CMS Confirmed',
      PACKAGE_REGISTERED: 'At Warehouse', ROUTE_ASSIGNED: 'Out for Delivery',
      DELIVERED: 'Delivered', FAILED: 'Failed',
    };

    function renderOrders() {
      const tb = document.getElementById('orders-body');
      if (!S.orders.length) {
        tb.innerHTML = `<tr><td colspan="5"><div class="empty"><div class="empty-icon">📦</div>No orders yet. Submit your first order above.</div></td></tr>`;
        return;
      }
      tb.innerHTML = S.orders.map(o => `
    <tr>
      <td><span class="mono" style="font-size:11px;color:var(--text2)">${o.id.substring(0, 12)}…</span></td>
      <td style="max-width:170px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${o.destination}</td>
      <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text2)">${o.description}</td>
      <td><span class="pill s-${o.status}">${STATUS_LABEL[o.status] || o.status}</span></td>
      <td style="white-space:nowrap">
        <button class="btn btn-ghost btn-sm" onclick="openTracking('${o.id}')">Track</button>
        <button class="btn btn-ghost btn-sm" onclick="refreshOne('${o.id}')" title="Refresh status">↻</button>
      </td>
    </tr>`).join('');
    }

    function updateClientStats() {
      const os = S.orders;
      document.getElementById('s-total').textContent = os.length;
      document.getElementById('s-active').textContent = os.filter(o => !['DELIVERED', 'FAILED'].includes(o.status)).length;
      document.getElementById('s-done').textContent = os.filter(o => o.status === 'DELIVERED').length;
      document.getElementById('s-fail').textContent = os.filter(o => o.status === 'FAILED').length;
    }

    async function refreshOne(id) {
      try {
        const o = await req(CFG.ORDER, `/api/v1/orders/${id}`);
        upsertOrder(o); renderOrders(); updateClientStats();
        toast(`Refreshed ${id.substring(0, 8)}…`, 'info');
      } catch (e) { toast('Refresh failed: ' + e.message, 'error'); }
    }

    // ─── SUBMIT ORDER ───
    async function submitOrder() {
      const btn = document.getElementById('submit-btn');
      const destination = v('o-dest'), description = v('o-desc');
      if (!destination || !description) { toast('Fill destination and description', 'error'); return; }
      setBtn(btn, true, 'Submitting…');
      try {
        const o = await req(CFG.ORDER, '/api/v1/orders', 'POST', { destination, description });
        S.orders.unshift(o);
        renderOrders(); updateClientStats();
        toast('Order submitted: ' + o.id.substring(0, 8) + '…', 'success');
        document.getElementById('o-dest').value = '';
        document.getElementById('o-desc').value = '';
        // Switch to orders tab
        document.querySelector('#client-view .tabs .tab').click();
      } catch (e) { toast('Error: ' + e.message, 'error'); }
      finally { setBtn(btn, false, 'Submit Order'); }
    }

    // ─── TRACKING MODAL ───
    const TL_STEPS = [
      { key: 'CREATED', label: 'Order submitted' },
      { key: 'CMS_CONFIRMED', label: 'Confirmed by Client Management System' },
      { key: 'PACKAGE_REGISTERED', label: 'Package registered at Warehouse (WMS)' },
      { key: 'ROUTE_ASSIGNED', label: 'Route optimised — Out for delivery (ROS)' },
      { key: 'DELIVERED', label: 'Delivered to recipient ✓' },
    ];
    const TL_ORDER = ['CREATED', 'CMS_CONFIRMED', 'PACKAGE_REGISTERED', 'ROUTE_ASSIGNED', 'DELIVERED'];

    async function openTracking(id) {
      // Refresh from backend first
      try {
        const fresh = await req(CFG.ORDER, `/api/v1/orders/${id}`);
        upsertOrder(fresh); renderOrders(); updateClientStats();
      } catch { }
      const o = S.orders.find(x => x.id === id);
      if (!o) return;
      document.getElementById('track-title').textContent = `Order ${o.id.substring(0, 12)}…`;
      document.getElementById('track-sub').textContent = o.destination;

      const curIdx = TL_ORDER.indexOf(o.status);
      const tl = document.getElementById('track-tl');
      tl.innerHTML = TL_STEPS.map((s, i) => {
        let cls = '';
        if (o.status !== 'FAILED') {
          if (i < curIdx) cls = 'done';
          else if (i === curIdx) cls = 'cur';
        } else {
          // Mark up to ROUTE_ASSIGNED as done, then show fail
          if (i < 3) cls = 'done';
        }
        return `<div class="tl-item ${cls}"><div class="tl-dot"></div><div class="tl-label">${s.label}</div></div>`;
      }).join('') + (o.status === 'FAILED' ? `<div class="tl-item fail"><div class="tl-dot"></div><div class="tl-label">Delivery failed — Saga compensation triggered</div></div>` : '');

      openModal('track-modal');
    }

    // ─── DRIVER ───
    function renderDriver() {
      const el = document.getElementById('dlv-list');
      const pending = S.orders.filter(o => o.status === 'ROUTE_ASSIGNED');
      const done = S.orders.filter(o => ['DELIVERED', 'FAILED'].includes(o.status));
      const other = S.orders.filter(o => !['ROUTE_ASSIGNED', 'DELIVERED', 'FAILED'].includes(o.status));

      let html = '';
      if (!S.orders.length) {
        html = `<div style="color:var(--text3);font-size:13px;padding:8px 0">No deliveries loaded. Use the "Order Lookup" panel to fetch orders, or orders will appear automatically via real-time events.</div>`;
      } else {
        pending.forEach((o, i) => {
          html += `<div class="dlv-card">
        <div class="stop-num">${i + 1}</div>
        <div class="dlv-info">
          <div class="dlv-addr">${o.destination}</div>
          <div class="dlv-meta mono" style="font-size:11px">${o.id.substring(0, 14)}… · ${o.description}</div>
        </div>
        <div class="dlv-actions">
          <button class="btn btn-green btn-sm" onclick="openPOD('${o.id}')">Deliver</button>
          <button class="btn btn-red btn-sm" onclick="openFail('${o.id}')">Fail</button>
        </div>
      </div>`;
        });
        if (other.length) {
          html += `<div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;margin:14px 0 8px">Other statuses</div>`;
          other.forEach(o => {
            html += `<div class="dlv-card">
          <div class="stop-num" style="color:var(--text3)">—</div>
          <div class="dlv-info"><div class="dlv-addr">${o.destination}</div><div class="dlv-meta">${o.description}</div></div>
          <span class="pill s-${o.status}">${STATUS_LABEL[o.status] || o.status}</span>
        </div>`;
          });
        }
        if (done.length) {
          html += `<div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;margin:14px 0 8px">Completed</div>`;
          done.forEach(o => {
            html += `<div class="dlv-card done">
          <div class="stop-num" style="color:var(--green);border-color:rgba(34,197,94,.3)">✓</div>
          <div class="dlv-info"><div class="dlv-addr">${o.destination}</div><div class="dlv-meta">${o.description}</div></div>
          <span class="pill s-${o.status}">${STATUS_LABEL[o.status] || o.status}</span>
        </div>`;
          });
        }
      }
      el.innerHTML = html;
      updateDriverStats();
    }

    function updateDriverStats() {
      const os = S.orders;
      document.getElementById('d-total').textContent = os.length;
      document.getElementById('d-done').textContent = os.filter(o => o.status === 'DELIVERED').length;
      document.getElementById('d-rem').textContent = os.filter(o => o.status === 'ROUTE_ASSIGNED').length;
      document.getElementById('d-fail').textContent = os.filter(o => o.status === 'FAILED').length;
    }

    async function driverLookup() {
      const input = document.getElementById('drv-lookup');
      const id = input.value.trim();
      if (!id) { toast('Enter an order ID', 'error'); return; }
      try {
        const o = await req(CFG.ORDER, `/api/v1/orders/${id}`);
        upsertOrder(o);
        renderDriver();
        input.value = '';
        toast(`Loaded: ${o.id.substring(0, 10)}… (${STATUS_LABEL[o.status] || o.status})`, 'success');
      } catch (e) { toast('Not found: ' + e.message, 'error'); }
    }

    // ─── POD ───
    function openPOD(id) {
      S.podId = id;
      const o = S.orders.find(x => x.id === id);
 
      openModal('pod-modal');
    }

    async function confirmDeliver() {
      const btn = document.getElementById('pod-btn');
      const sigUrl = v('sig-url');
      const podUrl = v('pod-image-url');
      let body = {
        digital_signature_url: sigUrl || null,
        pod_image_url: podUrl || null
      }
      setBtn(btn, true, 'Confirming…');
      try {
        // POST /api/v1/drivers/{driver_id}/deliveries/{order_id}/complete
        await req(CFG.ORDER, `/api/v1/drivers/${S.userId}/deliveries/${S.podId}/complete`, 'POST', body=body);
        // Backend will publish order.delivered → WS → auto-refresh
        // Also update locally immediately
        upsertOrder({ ...S.orders.find(o => o.id === S.podId), status: 'DELIVERED' });
        renderDriver(); updateDriverStats();
        closeModal('pod-modal');
        toast('Delivery confirmed ✓', 'success');
      } catch (e) { toast('Error: ' + e.message, 'error'); }
      finally { setBtn(btn, false, '✓ Confirm Delivered'); }
    }

    // ─── FAIL ───
    function openFail(id) {
      S.failId = id;
      const o = S.orders.find(x => x.id === id);
      document.getElementById('fail-sub').textContent = o ? o.destination : id;
      openModal('fail-modal');
    }

    async function confirmFail() {
      const btn = document.getElementById('fail-btn');
      setBtn(btn, true, 'Marking…');
      const reason = v('fail-reason');
      if (!reason) { toast('Enter failure reason', 'error'); setBtn(btn, false, 'Mark as Failed'); return; }
      const payload = { failed_reason: reason };
      await fetch(`${CFG.ORDER}/api/v1/drivers/${S.userId}/deliveries/${S.failId}/fail`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${S.token}` },
        body: JSON.stringify(payload),
      }).then(res => {
        if (!res.ok) return res.json().then(data => { throw new Error(data.detail || `HTTP ${res.status}`); });
      });
      
      try {
        const idx = S.orders.findIndex(o => o.id === S.failId);
        if (idx !== -1) S.orders[idx] = { ...S.orders[idx], status: 'FAILED' };
        renderDriver(); updateDriverStats();
        closeModal('fail-modal');
        toast(`Marked as failed: ${document.getElementById('fail-reason').value}`, 'error');
      } finally { setBtn(btn, false, 'Mark as Failed'); }
    }

    // ─── SIGNATURE ───
    function initSig() {
      const wrap = document.getElementById('sig-wrap');
      const canvas = document.getElementById('sig-canvas');
      const ctx = canvas.getContext('2d');
      const hint = document.getElementById('sig-hint');

      function resize() {
        const r = wrap.getBoundingClientRect();
        canvas.width = r.width || 360;
        canvas.height = 130;
        ctx.strokeStyle = '#e2e5eb';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
      }

      function pos(e) {
        const r = canvas.getBoundingClientRect();
        const s = e.touches ? e.touches[0] : e;
        return { x: s.clientX - r.left, y: s.clientY - r.top };
      }

      wrap.addEventListener('mousedown', e => {
        S.sigDown = true; S.sigHasContent = true;
        hint.classList.add('hidden'); resize();
        const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y);
      });
      wrap.addEventListener('mousemove', e => {
        if (!S.sigDown) return;
        const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke();
      });
      document.addEventListener('mouseup', () => S.sigDown = false);
      wrap.addEventListener('touchstart', e => {
        e.preventDefault(); S.sigDown = true; S.sigHasContent = true;
        hint.classList.add('hidden'); resize();
        const p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y);
      }, { passive: false });
      wrap.addEventListener('touchmove', e => {
        e.preventDefault();
        if (!S.sigDown) return;
        const p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke();
      }, { passive: false });
      wrap.addEventListener('touchend', () => S.sigDown = false);
      resize();
    }

    function clearSig() {
      const canvas = document.getElementById('sig-canvas');
      canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
      S.sigHasContent = false;
      document.getElementById('sig-hint').classList.remove('hidden');
    }

    // ─── HELPERS ───
    function v(id) { return document.getElementById(id)?.value.trim() || ''; }
    function setBtn(btn, disabled, txt) {
      btn.disabled = disabled;
      btn.innerHTML = disabled ? `<span class="spinner"></span> ${txt}` : txt;
    }

    // ─── INIT ───
    document.addEventListener('DOMContentLoaded', () => {
      show('login-screen');
      // initSig();

      // Enter key support
      ['l-user', 'l-pass'].forEach(id => {
        document.getElementById(id)?.addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
      });

      // Close modals on backdrop click
      document.querySelectorAll('.modal-bg').forEach(bg => {
        bg.addEventListener('click', e => { if (e.target === bg) bg.classList.remove('open'); });
      });

      // Lookup enter key
      document.getElementById('drv-lookup')?.addEventListener('keydown', e => { if (e.key === 'Enter') driverLookup(); });
    });
  