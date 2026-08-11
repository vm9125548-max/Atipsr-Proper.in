// Atipsr Pro: Website Activity & History Tracker
export const HistoryTracker = {
    // गतिविधि या हिस्ट्री सेव करने का फंक्शन
    logActivity(actionType, details) {
        try {
            const timestamp = new Date().toLocaleString();
            const logEntry = {
                time: timestamp,
                action: actionType,
                info: details
            };

            // पुरानी हिस्ट्री निकालकर उसमें नया वाला जोड़ना
            let historyList = JSON.parse(localStorage.getItem('studio_activity_history') || '[]');
            historyList.unshift(logEntry); // नया वाला सबसे ऊपर रहेगा

            // ज्यादा लोड न पड़े इसलिए सिर्फ आखिरी 50 गतिविधियाँ सेव रखेंगे
            if (historyList.length > 50) {
                historyList.pop();
            }

            localStorage.setItem('studio_activity_history', JSON.stringify(historyList));
            console.log("Activity Logged Successfully:", logEntry);
        } catch (err) {
            console.error("History Tracking Error:", err);
        }
    },

    // सारी हिस्ट्री देखने का फंक्शन (ताकि आप एडमिन पैनल या कंसोल में देख सकें)
    getHistory() {
        return JSON.parse(localStorage.getItem('studio_activity_history') || '[]');
    },

    // हिस्ट्री साफ करने का फंक्शन
    clearHistory() {
        localStorage.removeItem('studio_activity_history');
    }
};
