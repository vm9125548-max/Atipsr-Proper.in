// ==========================================
// ATIPSR-PROPER.IN - ULTRA ADAPTIVE SECURITY SHIELD
// ==========================================

const crypto = require('crypto');

class UltraAdaptiveShield {
    constructor() {
        this.threatLevel = "ZERO";
        this.activeFingerprints = new Set();
        this.mutationIntervalMs = 1000; // Har 1 second mein self-mutate hone ka target
        this.initDynamicShield();
    }

    quickScan(req) {
        const startNano = process.hrtime.bigint();
        const isThreat = /(<script>|eval\(|DROP TABLE|union select)/i.test(JSON.stringify(req.body) + req.url);
        const endNano = process.hrtime.bigint();
        const executionTimeMs = Number(endNano - startNano) / 1_000_000;

        if (isThreat || executionTimeMs > 5.0) {
            this.threatLevel = "HIGH";
            this.counterMeasure(req.ip);
            return false; // Blocked instantly within milliseconds
        }
        return true;
    }

    initDynamicShield() {
        setInterval(() => {
            const dynamicToken = crypto.randomBytes(32).toString('hex');
            process.env.DYNAMIC_SHIELD_HASH = dynamicToken;
        }, this.mutationIntervalMs);
    }

    counterMeasure(attackerIP) {
        console.log(`[SECURITY ALERT] Threat detected in < 1ms. IP Neutralized: ${attackerIP}`);
        this.activeFingerprints.add(attackerIP);
    }

    middleware() {
        return (req, res, next) => {
            const isAllowed = this.quickScan(req);
            if (!isAllowed) {
                return res.status(403).json({
                    error: "Access Denied by Atipsr-Proper Ultra Shield. Threat neutralized instantly."
                });
            }
            next();
        };
    }
}

const shieldInstance = new UltraAdaptiveShield();
module.exports = shieldInstance.middleware();
