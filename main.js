let worksList = [];

async function fetchCMSData() {
    try {
        const response = await fetch('works.json');
        if (response.ok) {
            const data = await response.json();
            if (data.worksList && data.worksList.length > 0) worksList = data.worksList; 
        }
    } catch (error) { console.error("加载失败", error); }
    renderWorks(); 
}

window.addEventListener('load', () => {
    const island = document.getElementById('islandContainer');
    if(island) island.classList.add('reveal-up');
    fetchCMSData();
});

let toastTimeout;
window.showToast = function(message, isError = false) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    if(toast) {
        toastMessage.textContent = message;
        toast.classList.remove('opacity-0'); toast.classList.add('opacity-100');
        clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => { toast.classList.remove('opacity-100'); toast.classList.add('opacity-0'); }, 2500);
    }
}

const themeToggleBtns = [document.getElementById('themeToggleBtn'), document.getElementById('themeToggleBtnMobile')];
const themeIcons = [document.getElementById('themeIcon'), document.getElementById('themeIconMobile')];
if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark-mode');
    themeIcons.forEach(icon => { icon.classList.remove('fa-moon-o'); icon.classList.add('fa-sun-o'); });
}
themeToggleBtns.forEach(btn => {
    if(btn) btn.addEventListener('click', (e) => {
        e.preventDefault(); document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        themeIcons.forEach(icon => {
            if (isDark) { icon.classList.remove('fa-moon-o'); icon.classList.add('fa-sun-o'); } 
            else { icon.classList.remove('fa-sun-o'); icon.classList.add('fa-moon-o'); }
        });
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });
});

const observerOptions = { threshold: 0.1, rootMargin: "0px 0px -50px 0px" };
const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (entry.isIntersecting) { entry.target.classList.add('revealed'); observer.unobserve(entry.target); }
    });
}, observerOptions);
function bindObserver() { document.querySelectorAll('.reveal-up:not(#islandContainer)').forEach(el => observer.observe(el)); }

let currentPage = 1; const itemsPerPage = 6; let totalPages = 1;
const gridElement = document.getElementById('worksGrid');
const pageIndicator = document.getElementById('pageIndicator');

function renderWorks() {
    gridElement.innerHTML = ''; 
    totalPages = Math.max(1, Math.ceil(worksList.length / itemsPerPage));
    const startIdx = (currentPage - 1) * itemsPerPage;
    const currentWorks = worksList.slice(startIdx, startIdx + itemsPerPage);

    currentWorks.forEach((work, index) => {
        const delay = index * 0.1; 
        const coverUrl = work.cover ? work.cover : 'images/placeholder.jpg';
        const cardHTML = `
            <div class="liquid-glass hover-elastic flex flex-col cursor-pointer reveal-up" style="transition-delay: ${delay}s;" onclick="openWork('${work.id}')">
                <div class="aspect-[4/3] overflow-hidden relative border-b border-[var(--glass-border)] z-0 rounded-t-[24px]">
                    <img src="${coverUrl}" alt="${work.title}" class="w-full h-full object-cover glass-card-img" loading="lazy">
                </div>
                <div class="p-4 md:p-8 flex-1 pointer-events-none relative z-0 flex flex-col justify-center">
                    <h3 class="text-[clamp(12px,3.5vw,20px)] font-extrabold mb-1.5 md:mb-2 tracking-wide color-main leading-snug line-clamp-2">${work.title}</h3>
                    <p class="color-muted font-medium text-[clamp(10px,2.8vw,14px)] leading-relaxed tracking-wide opacity-90 line-clamp-2">${work.desc}</p>
                </div>
            </div>
        `;
        gridElement.insertAdjacentHTML('beforeend', cardHTML);
    });

    const remainingSlots = itemsPerPage - currentWorks.length;
    if (remainingSlots > 0 && remainingSlots < itemsPerPage) {
        for (let i = 0; i < remainingSlots; i++) {
            const delay = (currentWorks.length + i) * 0.1;
            const placeholderHTML = `
                <div class="flex flex-col justify-center items-center h-full reveal-up relative overflow-hidden group rounded-[24px]" style="border: 1px dashed rgba(150, 150, 150, 0.35); transition-delay: ${delay}s;">
                    <div class="flex flex-col items-center justify-center p-4 md:p-8 opacity-40 group-hover:opacity-100 transition-all duration-700 transform group-hover:scale-105 w-full">
                        <div class="w-10 h-10 md:w-12 md:h-12 rounded-full border border-[var(--text-muted)] flex items-center justify-center mb-4 md:mb-5 opacity-80"><i class="fa fa-hourglass-half text-[var(--text-muted)] text-[10px] md:text-sm"></i></div>
                        <p class="text-[8px] md:text-[9px] font-black uppercase tracking-[0.4em] color-muted mb-2 md:mb-3 pl-[0.4em] text-center w-full">TO BE CONTINUED</p>
                        <h3 class="text-[11px] sm:text-[12px] md:text-[14px] font-bold tracking-[0.2em] color-main text-center leading-relaxed pl-[0.2em] w-full">作品持续更新中<br>敬请期待</h3>
                    </div>
                </div>
            `;
            gridElement.insertAdjacentHTML('beforeend', placeholderHTML);
        }
    }
    if(pageIndicator) pageIndicator.textContent = `${currentPage} / ${totalPages}`;
    setTimeout(bindObserver, 50);
}

if(document.getElementById('firstPageBtn')) {
    document.getElementById('firstPageBtn').addEventListener('click', () => { if(currentPage !== 1) { currentPage = 1; renderWorks(); }});
    document.getElementById('prevPageBtn').addEventListener('click', () => { if(currentPage > 1) { currentPage--; renderWorks(); }});
    document.getElementById('nextPageBtn').addEventListener('click', () => { if(currentPage < totalPages) { currentPage++; renderWorks(); }});
    document.getElementById('lastPageBtn').addEventListener('click', () => { if(currentPage !== totalPages) { currentPage = totalPages; renderWorks(); }});
}

const workModal = document.getElementById('workModal');
const closeWorkModal = document.getElementById('closeWorkModal');
const modalImageContainer = document.getElementById('modalImageContainer');
const workModalScrollBox = document.getElementById('workModalScrollBox');
const loadingSpinner = document.getElementById('loadingSpinner');
const zoomText = document.getElementById('zoomText');
const scrollTopDetailBtn = document.getElementById('scrollTopDetailBtn');

let currentScale = 100; const zoomStep = 25; const maxScale = 250; const minScale = 50;    
const baseContainerWidth = 900; 

window.openWork = function(workId) {
    const work = worksList.find(w => String(w.id) === String(workId));
    if (work) {
        modalImageContainer.innerHTML = ''; 
        modalImageContainer.classList.remove('copyright-blurred');
        document.getElementById('copyrightOverlay').classList.replace('opacity-100', 'opacity-0');
        document.getElementById('copyrightOverlay').classList.replace('pointer-events-auto', 'pointer-events-none');
        
        loadingSpinner.classList.add('hidden'); 
        modalImageContainer.classList.remove('opacity-0'); 
        modalImageContainer.classList.add('opacity-100');
        
        currentScale = 100; zoomText.textContent = '100%';
        scrollTopDetailBtn.classList.remove('scroll-top-enabled'); scrollTopDetailBtn.classList.add('scroll-top-disabled');
        
        const blocksContainer = document.createElement('div');
        blocksContainer.id = "blocksContainer"; 
        blocksContainer.className = "w-full mx-auto px-4 md:px-12 py-10 md:py-16 flex flex-col gap-8 md:gap-12";
        blocksContainer.style.maxWidth = `${baseContainerWidth}px`;
        blocksContainer.style.fontSize = `100%`; 
        
        const watermark = document.createElement('div');
        watermark.className = 'watermark-layer';
        blocksContainer.appendChild(watermark);

        const titleBlock = document.createElement('h1');
        titleBlock.className = "text-4xl md:text-5xl lg:text-6xl font-black color-main tracking-tighter mb-8 mt-8 md:mt-12 text-balance leading-tight text-center md:text-left relative z-[21]";
        titleBlock.innerHTML = work.title;
        blocksContainer.appendChild(titleBlock);

        const blocksToLoad = work.blocks && work.blocks.length > 0 ? work.blocks : 
                            (work.images && work.images.length > 0 ? work.images.map(img => ({type: 'image', src: img})) : []);

        if (blocksToLoad.length > 0) {
            blocksToLoad.forEach((block) => {
                let el;
                if (block.type === 'h1') {
                    el = document.createElement('h2');
                    el.className = `text-3xl md:text-4xl font-extrabold color-main tracking-tight mt-12 md:mt-16 mb-4 border-b-2 border-[var(--text-main)] pb-4 opacity-90 relative z-[21]`;
                    el.innerHTML = block.html;
                } 
                else if (block.type === 'h2') {
                    el = document.createElement('h3');
                    el.className = `text-xl md:text-2xl font-bold color-main tracking-wide mt-10 md:mt-12 mb-2 border-l-[5px] border-[var(--text-main)] pl-4 opacity-85 relative z-[21]`;
                    el.innerHTML = block.html;
                } 
                else if (block.type === 'p') {
                    el = document.createElement('p');
                    el.className = `text-[16px] md:text-[18px] leading-[2.2] font-medium color-main opacity-80 tracking-[0.05em] text-justify text-balance relative z-[21]`;
                    el.innerHTML = block.html;
                } 
                else if (block.type === 'quote') {
                    el = document.createElement('blockquote');
                    el.className = `bg-[var(--glass-bg)] border-l-[4px] border-[var(--text-main)] p-6 md:p-8 my-8 md:my-10 text-xl md:text-2xl font-serif italic color-main opacity-75 rounded-r-xl shadow-sm relative z-[21]`;
                    el.innerHTML = block.html;
                }
                else if (block.type === 'divider') {
                    el = document.createElement('div');
                    el.className = `flex justify-center items-center my-10 opacity-30 relative z-[21]`;
                    el.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-[var(--text-main)] mx-2"></span><span class="w-2.5 h-2.5 rounded-full bg-[var(--text-main)] mx-2"></span><span class="w-1.5 h-1.5 rounded-full bg-[var(--text-main)] mx-2"></span>`;
                }
                else if (block.type === 'image') {
                    el = document.createElement('div');
                    el.className = `w-full relative rounded-xl md:rounded-2xl overflow-hidden bg-[var(--glass-bg)] min-h-[20vh] shadow-lg my-2 relative z-[21]`;
                    const img = document.createElement('img');
                    img.src = block.src;
                    img.className = "relative z-[1] block w-full h-auto pointer-events-none transform transition-transform duration-[1s] hover:scale-[1.01]";
                    img.loading = "lazy"; 
                    el.appendChild(img);
                }

                if (el) blocksContainer.appendChild(el);
            });
        } else {
            blocksContainer.innerHTML = '<div class="py-20 text-center color-muted tracking-widest text-sm font-bold">作品排版内容加载中...</div>';
        }

        modalImageContainer.appendChild(blocksContainer);
        workModalScrollBox.scrollTop = 0; 
        workModal.classList.add('active'); 
        document.body.style.overflow = 'hidden';
    }
};

function updateZoom(newScale) {
    currentScale = Math.max(minScale, Math.min(maxScale, newScale));
    const container = document.getElementById('blocksContainer');
    if(container) {
        container.style.maxWidth = `${baseContainerWidth * (currentScale / 100)}px`;
        container.style.fontSize = `${currentScale}%`;
    }
    zoomText.textContent = `${currentScale}%`;
}
if(document.getElementById('zoomInBtn')) document.getElementById('zoomInBtn').addEventListener('click', (e) => { e.stopPropagation(); updateZoom(currentScale + zoomStep); });
if(document.getElementById('zoomOutBtn')) document.getElementById('zoomOutBtn').addEventListener('click', (e) => { e.stopPropagation(); updateZoom(currentScale - zoomStep); });

if(workModalScrollBox) workModalScrollBox.addEventListener('scroll', () => {
    if (workModalScrollBox.scrollTop > 400) { scrollTopDetailBtn.classList.add('scroll-top-enabled'); scrollTopDetailBtn.classList.remove('scroll-top-disabled'); } 
    else { scrollTopDetailBtn.classList.remove('scroll-top-enabled'); scrollTopDetailBtn.classList.add('scroll-top-disabled'); }
});
if(scrollTopDetailBtn) scrollTopDetailBtn.addEventListener('click', (e) => { e.stopPropagation(); workModalScrollBox.scrollTo({ top: 0, behavior: 'smooth' }); });

const closeWork = () => {
    workModal.classList.remove('active'); document.body.style.overflow = '';
    setTimeout(() => { modalImageContainer.innerHTML = ''; modalImageContainer.classList.remove('opacity-100'); modalImageContainer.classList.add('opacity-0'); }, 400); 
};
if(closeWorkModal) closeWorkModal.addEventListener('click', closeWork);
if(workModal) workModal.addEventListener('click', (e) => { if (e.target === workModal) closeWork(); });

let isCopyrightUnlocked = false;
function triggerCopyrightDefense(reason) {
    if (isCopyrightUnlocked) return; 
    if (workModal.classList.contains('active')) {
        modalImageContainer.classList.add('copyright-blurred');
        document.getElementById('copyrightOverlay').classList.remove('opacity-0', 'pointer-events-none');
        document.getElementById('copyrightOverlay').classList.add('opacity-100', 'pointer-events-auto');
        document.getElementById('copyrightBox').classList.remove('scale-95');
        document.getElementById('copyrightBox').classList.add('scale-100');
        
        setTimeout(() => document.getElementById('copyrightPassword').focus(), 100);
        showToast(`访问受限：已拦截系统级 [ ${reason} ] 指令`, true);
    } else {
        showToast(`私密资产：本站已限制 [ ${reason} ] 权限`, true);
    }
}

document.addEventListener('contextmenu', (e) => { if (!isCopyrightUnlocked) { e.preventDefault(); triggerCopyrightDefense("右键菜单"); } });
document.addEventListener('copy', (e) => { if (!isCopyrightUnlocked) { e.preventDefault(); triggerCopyrightDefense("内容复制"); } });
document.addEventListener('keydown', (e) => {
    if (isCopyrightUnlocked) return;
    if (e.key === 'PrintScreen') { triggerCopyrightDefense("物理截屏"); navigator.clipboard.writeText("私密数字资产，禁止截屏获取。").catch(()=>{}); }
    if (e.metaKey && e.shiftKey && (e.key === '3' || e.key === '4' || e.key === '5' || e.key === 's' || e.key === 'S')) { triggerCopyrightDefense("快捷截屏"); }
    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) { e.preventDefault(); triggerCopyrightDefense("网页另存为"); }
    if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P')) { e.preventDefault(); triggerCopyrightDefense("网页打印"); }
    if (e.key === 'F12' || ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'I' || e.key === 'i'))) { e.preventDefault(); triggerCopyrightDefense("开发者工具"); }
});

function verifyCopyrightUnlock() {
    const pwd = document.getElementById('copyrightPassword');
    if (pwd.value === '66668888') {
        isCopyrightUnlocked = true; 
        document.getElementById('copyrightOverlay').classList.replace('opacity-100', 'opacity-0');
        document.getElementById('copyrightOverlay').classList.replace('pointer-events-auto', 'pointer-events-none');
        document.getElementById('copyrightBox').classList.replace('scale-100', 'scale-95');
        modalImageContainer.classList.remove('copyright-blurred');
        showToast("秘钥验证通过，已为您开放全站权限。");
        pwd.value = '';
    } else {
        showToast("秘钥无效，访问拒绝", true);
        pwd.value = '';
        pwd.classList.add('shake-error');
        setTimeout(() => pwd.classList.remove('shake-error'), 400);
    }
}

if(document.getElementById('unlockCopyrightBtn')) document.getElementById('unlockCopyrightBtn').addEventListener('click', verifyCopyrightUnlock);
if(document.getElementById('copyrightPassword')) document.getElementById('copyrightPassword').addEventListener('keypress', (e) => { if(e.key === 'Enter') verifyCopyrightUnlock(); });
if(document.getElementById('closeCopyrightBtn')) document.getElementById('closeCopyrightBtn').addEventListener('click', () => {
    closeWork();
    setTimeout(() => {
        document.getElementById('copyrightOverlay').classList.replace('opacity-100', 'opacity-0');
        document.getElementById('copyrightOverlay').classList.replace('pointer-events-auto', 'pointer-events-none');
    }, 300);
});

const resumeModal = document.getElementById('resumeModal');
const openResumeBtn = document.getElementById('openResumeBtn');
const closeResumeModal = document.getElementById('closeResumeModal');
if(openResumeBtn) openResumeBtn.addEventListener('click', () => { resumeModal.classList.add('active'); document.body.style.overflow = 'hidden'; });
const closeResume = () => { resumeModal.classList.remove('active'); document.body.style.overflow = ''; };
if(closeResumeModal) closeResumeModal.addEventListener('click', closeResume);
if(resumeModal) resumeModal.addEventListener('click', (e) => { if (e.target === resumeModal) closeResume(); });

window.copyTextToClipboard = function(text, type) {
    navigator.clipboard.writeText(text).then(() => { showToast(`已成功复制${type}: ${text}`); })
    .catch(err => { showToast('复制失败，请手动选择复制', true); });
}
