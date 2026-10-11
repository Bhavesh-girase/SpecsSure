// SpecSure API client. All calls go through the Next.js rewrite (/api/v1 -> FastAPI) so no CORS setup is needed.
export const API = process.env.NEXT_PUBLIC_API_BASE || "/api/v1";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

export const get = <T = any>(path: string) => fetch(`${API}${path}`, { cache: "no-store" }).then((r) => handle<T>(r));
export const post = <T = any>(path: string, body?: any) =>
  fetch(`${API}${path}`, {
    method: "POST",
    headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  }).then((r) => handle<T>(r));
export const patch = <T = any>(path: string, body: any) =>
  fetch(`${API}${path}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then((r) => handle<T>(r));
export const fileUrl = (path: string) => `${API}${path}`;

// ---------------- legacy / standards recommendation ----------------
export async function analyzeSpecification(opts: { text?: string; file?: File; language?: string; maxDepth?: number }) {
  const fd = new FormData();
  if (opts.file) fd.append("file", opts.file);
  if (opts.text) fd.append("text", opts.text);
  fd.append("language", opts.language || "auto");
  fd.append("max_depth", String(opts.maxDepth ?? 2));
  return post("/analyze", fd);
}
export const getPastAnalysis = (id: string) => get(`/analyze/${encodeURIComponent(id)}`);
export const getSystemHealth = () => get("/health");
export const quickSearch = (query: string, top_k = 5) => post("/analyze/quick", { query, top_k });
export const searchStandards = (query: string, top_k = 20) => post("/search", { query, top_k });
export const getStandardDetail = (isNumber: string) => get(`/standards/${encodeURIComponent(isNumber)}`);
export const getStandardGraph = (isNumber: string, depth = 2) => get(`/standards/${encodeURIComponent(isNumber)}/graph?depth=${depth}`);

// ---------------- buyer: tender digital twin ----------------
export const listTenders = () => get<any[]>("/tenders");
export const getTender = (id: string) => get<{ summary: any; twin: any }>(`/tenders/${id}`);
export const createTender = (fd: FormData) => post("/tenders", fd);
export const addTenderDocument = (id: string, file: File, docType = "auto") => {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("doc_type", docType);
  return post(`/tenders/${id}/documents`, fd);
};
export const recompile = (id: string) => post(`/tenders/${id}/compile`);
export const updateTender = (id: string, body: { status?: string; as_of_date?: string }) => patch(`/tenders/${id}`, body);
export const reviewFinding = (id: string, fp: string, review_status: string, comment?: string, reviewer = "Tender Officer") =>
  patch(`/tenders/${id}/findings/${fp}`, { review_status, comment, reviewer });
export const autofix = (id: string, fingerprints: string[], apply = false) => post(`/tenders/${id}/autofix`, { fingerprints, apply });
export const prebidDecision = (id: string, qid: string, status: string, final_response?: string) =>
  post(`/tenders/${id}/prebid/${qid}`, { status, final_response });
export const prebidPropagate = (id: string, apply = false) => post(`/tenders/${id}/prebid-propagate`, { apply });
export const clauseHistory = (id: string, key: string) => get(`/tenders/${id}/clauses/${encodeURIComponent(key)}/history`);

// ---------------- demo ----------------
export const demoIds = () => get("/demo");
export const demoSeed = () => post("/demo/seed");
export const demoCorrigendum = (id: string, n: number) => post(`/demo/tenders/${id}/corrigendum/${n}`);

// ---------------- bidder ----------------
export const listBids = (tenderId?: string) => get<any[]>(`/bids${tenderId ? `?tender_id=${tenderId}` : ""}`);
export const getBid = (id: string) => get(`/bids/${id}`);
export const createBid = (fd: FormData) => post("/bids", fd);
export const issuePassport = (bidId: string) => post(`/bids/${bidId}/passport`);
export const getPassport = (id: string) => get(`/passports/${id}`);
export const listPassports = () => get<any[]>("/passports");
export const verifyCredential = (vc: any) => post("/passports/verify", vc);

// ---------------- radar / intel / governance ----------------
export const radarScenarios = () => get<any[]>("/radar/scenarios");
export const radarSimulate = (key: string) => post(`/radar/simulate/${key}`);
export const radarEvents = () => get<any[]>("/radar/events");
export const radarImpact = (standard: string) => get(`/radar/impact?standard=${encodeURIComponent(standard)}`);
export const qcoImpact = () => get<any[]>("/radar/qco-impact");
export const radarWatch = () => post("/radar/watch");
export const notifications = () => get<any[]>("/notifications");
export const markNotificationsRead = () => post("/notifications/read");
export const temporalResolve = (citation: string, asOf?: string) =>
  get(`/temporal/resolve?citation=${encodeURIComponent(citation)}${asOf ? `&as_of=${asOf}` : ""}`);
export const temporalTimeline = (citation: string) => get(`/temporal/timeline?citation=${encodeURIComponent(citation)}`);
export const equivalenceStandards = () => get("/equivalence/standards");
export const compareStandards = (a: string, b: string, ga?: string, gb?: string) =>
  get(`/equivalence?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}${ga ? `&grade_a=${encodeURIComponent(ga)}` : ""}${gb ? `&grade_b=${encodeURIComponent(gb)}` : ""}`);
export const addReview = (body: any) => post("/reviews", body);
export const lintText = (text: string, as_of?: string) => post("/lint", { text, as_of });
export const rules = () => get<any[]>("/rules");
export const memorySearch = (q: string) => get(`/memory/search?q=${encodeURIComponent(q)}`);
export const ledger = (subjectId?: string) => get<any[]>(`/ledger?limit=200${subjectId ? `&subject_id=${subjectId}` : ""}`);
export const ledgerVerify = () => get("/ledger/verify");
export const explainFinding = (id: string, fp: string, lang = "hi") => post(`/tenders/${id}/findings/${fp}/explain`, { lang });
export const rerunBid = (id: string) => post(`/bids/${id}/rerun`);

// ---------------- Tender Studio (intent → verified tender) ----------------
export const studioCatalogue = () => get("/studio/catalogue");
export const studioParse = (text: string) => post("/studio/parse", { text });
export const studioGenerate = (body: { intent: any; answers?: any; as_of?: string; meta?: any; overrides?: any }) => post("/studio/generate", body);
export const studioSave = (body: { intent: any; answers?: any; as_of?: string; meta?: any; overrides?: any; publish?: boolean }) => post("/studio/save", body);
export async function studioDocx(generation: any) {
  const res = await fetch(`${API}/studio/docx`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ generation }) });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.blob();
}
export const tenderGeneration = (id: string) => get(`/tenders/${id}/generation`);

// ---------------- Procurement Knowledge Graph ----------------
export const kgStats = () => get("/kg/stats");
export const kgSearch = (q: string) => get<any[]>(`/kg/search?q=${encodeURIComponent(q)}`);
export const kgNode = (id: string, depth = 1, asOf?: string, limit = 80) =>
  get(`/kg/node?id=${encodeURIComponent(id)}&depth=${depth}&limit=${limit}${asOf ? `&as_of=${asOf}` : ""}`);
export const kgItem = (itemId: string, asOf?: string) => get(`/kg/items/${itemId}${asOf ? `?as_of=${asOf}` : ""}`);
export const kgPath = (a: string, b: string) => get(`/kg/path?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);

// ---------------- Contractor marketplace & smart bid form ----------------
export const marketTenders = () => get<any[]>("/market/tenders");
export const bidForm = (tenderId: string) => get(`/tenders/${tenderId}/bid-form`);
export const bidFormScore = (tenderId: string, answers: any, scope?: string[] | null) => post(`/tenders/${tenderId}/bid-form/score`, { answers, scope });
export const bidFormAutofill = (tenderId: string, files: File[]) => {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  return post(`/tenders/${tenderId}/bid-form/autofill`, fd);
};
export const bidFormSubmit = (tenderId: string, bidder: string, productName: string, answers: any, scope: string[] | null, files: File[]) => {
  const fd = new FormData();
  fd.append("bidder", bidder);
  if (productName) fd.append("product_name", productName);
  fd.append("answers", JSON.stringify(answers));
  if (scope?.length) fd.append("scope", scope.join(","));
  files.forEach((f) => fd.append("files", f));
  return post(`/tenders/${tenderId}/bid-form/submit`, fd);
};
export const comparativeStatement = (tenderId: string) => get(`/tenders/${tenderId}/comparative`);
export const ocrFile = (file: File) => { const fd = new FormData(); fd.append("file", file); return post("/ocr", fd); };
export const ocrEngines = () => get("/ocr/engines");

// ---------------- Lifecycle: queries, advice, evaluation, award, dashboards ----------------
export const portalStats = () => get("/stats");
export const officerDashboard = () => get("/dashboard/officer");
export const contractorDashboard = (bidder?: string) => get(`/dashboard/contractor${bidder ? `?bidder=${encodeURIComponent(bidder)}` : ""}`);
export const raiseQuery = (tenderId: string, bidder: string, question: string, clause_key?: string) =>
  post(`/tenders/${tenderId}/queries`, { bidder, question, clause_key });
export const listQueries = (tenderId: string, publicOnly = false) => get<any[]>(`/tenders/${tenderId}/queries${publicOnly ? "?public=true" : ""}`);
export const answerQuery = (tenderId: string, qid: string, response: string, status = "published") =>
  post(`/tenders/${tenderId}/queries/${qid}/answer`, { response, status, officer: "Tender Officer" });
export const bidAdvice = (tenderId: string, answers: any, scope?: string[] | null) => post(`/tenders/${tenderId}/bid-form/advice`, { answers, scope });
export const evaluation = (tenderId: string) => get(`/tenders/${tenderId}/evaluation`);
export const closeBidding = (tenderId: string) => post(`/tenders/${tenderId}/close-bidding`, { officer: "Tender Officer" });
export const openFinancial = (tenderId: string) => post(`/tenders/${tenderId}/open-financial`, { officer: "Tender Evaluation Committee" });
export const recordAward = (tenderId: string, remarks?: string) => post(`/tenders/${tenderId}/award`, { officer: "Tender Evaluation Committee", remarks });
export const bidFormSubmitSealed = (tenderId: string, body: { bidder: string; productName?: string; answers: any; scope: string[] | null; files: File[];
                                                          financial?: any; declarations?: any }) => {
  const fd = new FormData();
  fd.append("bidder", body.bidder);
  if (body.productName) fd.append("product_name", body.productName);
  fd.append("answers", JSON.stringify(body.answers));
  if (body.scope?.length) fd.append("scope", body.scope.join(","));
  if (body.financial) fd.append("financial", JSON.stringify(body.financial));
  if (body.declarations) fd.append("declarations", JSON.stringify(body.declarations));
  body.files.forEach((f) => fd.append("files", f));
  return post(`/tenders/${tenderId}/bid-form/submit`, fd);
};

// ---------------- Standards Recommender (full Indian Standards corpus) ----------------
export const corpusStats = () => get("/corpus/stats");
export const corpusRecommend = (query: string, top_k = 8, expand = 1, division?: string) => post("/corpus/recommend", { query, top_k, expand, division: division || null });
export const corpusStandard = (base: string) => get(`/corpus/standard?base=${encodeURIComponent(base)}`);
export const corpusDependencyTree = (base: string, depth = 2) => get(`/corpus/dependency-tree?base=${encodeURIComponent(base)}&depth=${depth}`);
export const corpusLabs = (base: string, city?: string) => get(`/corpus/labs?base=${encodeURIComponent(base)}${city ? `&city=${encodeURIComponent(city)}` : ""}`);
export const corpusRecommendDocument = (file: File) => { const fd = new FormData(); fd.append("file", file); return post("/corpus/recommend-document", fd); };
export const specBlock = (base: string, item?: string) => get(`/corpus/spec-block?base=${encodeURIComponent(base)}${item ? `&item=${encodeURIComponent(item)}` : ""}`);
export async function specBlockDocx(blocks: { base: string; item?: string }[], title?: string) {
  const res = await fetch(`${API}/corpus/spec-block.docx`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ blocks, title }) });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.blob();
}
export const corpusEvidence = () => get("/corpus/evidence");
