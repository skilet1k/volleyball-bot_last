// Keep-alive script для Render.com
// Можно использовать с cron-job.org или uptimerobot.com

const https = require('https');

const URL = 'https://volleyball-bot-last.onrender.com/health';

function pingService() {
    const req = https.get(URL, (res) => {
        console.log(`Ping response: ${res.statusCode} at ${new Date().toISOString()}`);
    });
    
    req.on('error', (error) => {
        console.error(`Ping error: ${error.message} at ${new Date().toISOString()}`);
    });
    
    req.setTimeout(30000, () => {
        console.log('Ping timeout');
        req.destroy();
    });
}

// Пинг каждые 10 минут
setInterval(pingService, 10 * 60 * 1000);

// Первый пинг
pingService();

console.log('Keep-alive service started');
