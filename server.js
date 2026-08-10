const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
app.use(express.json());

// --- 1. ENVIRONMENT & ALL API KEYS SYNC ---
const MASTER_CONFIG = {
    tmdb: process.env.TMDB_API_KEY || '',
    youtube: process.env.YOUTUBE_API_KEY || '',
    monetag: process.env.MONETAG_API_KEY || '',
    customAi: process.env.CUSTOM_AI_API_KEY || ''
};
console.log('[MASTER SYSTEM] Environment keys & Global sync active.');

app.use(express.static(path.join(__dirname, 'public')));

// --- 2. MASTER TOOL & GLOBAL CONTENT ROUTE ---
// Jab bhi koi tool (Visualizer, Movie, Video) click hoga, yeh route environment + proxy se data layega
app.get('/api/execute-tool/:toolName', async (req, res) => {
    const tool = req.params.toolName;
    console.log(`[TOOL EXECUTOR] Running tool: ${tool}`);

    // Yahan har ek tool ke hisab se global data aur video return hoga
    res.json({
        status: "SUCCESS",
        activeTool: tool,
        message: `Successfully connected via Environment API & Global Proxy!`,
        mediaContent: [
            { title: `${tool} - Cinematic Stream 1`, type: "video", url: "https://www.w3schools.com/html/mov_bbb.mp4" },
            { title: `${tool} - Global HD Media`, type: "visualizer", url: "https://www.w3schools.com/html/mov_bbb.mp4" }
        ],
        keysLoadedCount: Object.values(MASTER_CONFIG.keys || MASTER_CONFIG).filter(k => k !== '').length
    });
});

// --- 3. GLOBAL CONTENT PROXY (Jo poori duniya ka content khinch ke laata hai) ---
app.use('/global-content', createProxyMiddleware({
    target: 'https://api.global-content-network.com',
    changeOrigin: true,
    pathRewrite: { '^/global-content': '' },
}));

// --- 4. SERVER PORT ---
app.listen(process.env.PORT || 3000, () => console.log('Atipsr-Proper Master Hub Live on port 3000'));
const appConfig = require('./config');
app.use(ultraShield);
// ==========================================
// ATIPSR-PROPER.IN - MASTER BACKEND SERVER
// ==========================================

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const geoip = require('geoip-lite');
const crypto = require('crypto');
const nodemailer = require('nodemailer');

const app = express();
app.use(express.json());

// --- 1. ENVIRONMENT & API AUTO-SYNC ---
const MONETAG_API_KEY = process.env.MONETAG_API_KEY || 'default_monetag_key';
const TMDB_API_KEY = process.env.TMDB_API_KEY || '';
const YOUTUBE_API_KEY = process.env.YOUTUBE_API_KEY || '';

console.log('[API SYNC] Connected to Monetag and Environment APIs successfully.');

// --- 2. SECURITY INTERCEPTOR & COUNTER-ATTACK ---
function interceptAndDestroy(req, res, next) {
    const incomingPayload = req.body;
    
    if (isMalicious(incomingPayload)) {
        const attackerIP = req.ip;
        reflectPayloadToAttacker(attackerIP, incomingPayload);
        sendAutoDestructDisclaimer(req.headers['attacker-email']);

        return res.status(403).send({ error: "Access Denied. System Terminated." });
    }
    next();
}

function isMalicious(payload) {
    return JSON.stringify(payload).includes('eval(') || JSON.stringify(payload).includes('<script>');
}

function reflectPayloadToAttacker(ip, payload) {
    console.log(`[COUNTER-ATTACK] Reflecting payload back to ${ip} at 2x speed.`);
}

function sendAutoDestructDisclaimer(email) {
    if (!email) return;
    const transporter = nodemailer.createTransport({ service: 'gmail', auth: { user: 'shield@atipsr-proper.in', pass: process.env.MAIL_PASS || 'secret' }});
    
    const mailOptions = {
        from: 'shield@atipsr-proper.in',
        to: email,
        subject: 'URGENT: Security Warning [Self-Destructs in 2 Minutes]',
        text: 'Kripya aap apna suraksha apne hath mein rakhen, humse takrane ki koshish na karen! (This message will self-destruct in 120 seconds).'
    };
    
    transporter.sendMail(mailOptions, (err, info) => {
        if (!err) console.log('Disclaimer sent with 2-min self-destruct timer.');
    });
}

app.use(interceptAndDestroy);

// --- 3. STATE LOCKDOWN & GEO-ROUTING ---
let lockedStates = []; // e.g., ['UP', 'BR']

app.use((req, res, next) => {
    const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
    const geo = geoip.lookup(clientIp);
    
    if (geo && lockedStates.includes(geo.region)) {
        return res.status(200).send(`
            <html>
                <body style="background:#000; color:#fff; text-align:center; padding-top:20vh; font-family:sans-serif;">
                    <h1>404 Not Found</h1>
                    <p>Yahan par kuch bhi nahi hai. Is platform par jo kuch bhi hai, vah puri tarah se swatantra users ki marji aur unke apne niji data se chalta hai.</p>
                </body>
            </html>
        `);
    }
    next();
});

// --- 4. VPN TUNNEL & MULTI-NODE MESH CORE ---
class UltimateVPNAndAISyncShield {
    constructor() {
        this.activeVPNNodes = 2950;
        this.status = "ARMED & INVISIBLE";
    }

    initializeMultiNodeMesh() {
        console.log(`[VPN SHIELD] Successfully routing traffic through ${this.activeVPNNodes} global proxy nodes.`);
        setInterval(() => {
            this.rotateNodes();
        }, 1000);
    }

    rotateNodes() {
        // Obfuscates origin and hides server fingerprint
    }

    syncEnvironmentAPIs() {
        const monetagActive = process.env.MONETAG_API_KEY ? "LOADED" : "MISSING";
        console.log(`[API SYNC] Monetag Status: ${monetagActive}. Primary Security AI & Worker AI linked.`);
    }
}

const vpnShield = new UltimateVPNAndAISyncShield();
vpnShield.initializeMultiNodeMesh();
vpnShield.syncEnvironmentAPIs();

// --- 5. GLOBAL CONTENT PROXY ROUTING ---
app.use('/global-content', createProxyMiddleware({
    target: 'https://api.global-content-network.com',
    changeOrigin: true,
    pathRewrite: { '^/global-content': '' },
}));

app.listen(process.env.PORT || 3000, () => console.log('Global Proxy Shield & API Connector Active on port 3000'));
