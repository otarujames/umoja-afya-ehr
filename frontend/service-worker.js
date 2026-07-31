const CACHE='umoja-afya-enterprise-v10.4.0';
const CORE=[
  '/', '/styles.css', '/app.js', '/manifest.json',
  '/assets/umoja-logo.svg',
  '/assets/avatars/neema-k.png',
  '/assets/avatars/juma-ally-mwangi.png',
  '/assets/tanzania-coat-of-arms.png'
];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(CORE))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))));
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET'||url.pathname.startsWith('/api/')) return;
  const staticAsset=['/','/styles.css','/app.js','/manifest.json','/assets/umoja-logo.svg','/assets/tanzania-coat-of-arms.png'].includes(url.pathname)||url.pathname.startsWith('/assets/');
  if(!staticAsset) return;
  event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{if(response.ok){const clone=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,clone));}return response;}).catch(()=>caches.match(event.request).then(cached=>cached||caches.match('/'))));
});
