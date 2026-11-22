import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronDown,
  Download,
  Heart,
  ImagePlus,
  LoaderCircle,
  Menu,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { api, assetUrl, wait, type Health } from "./api";
import { demoProducts, palette, type Product } from "./catalog";
import Garment from "./Garment";

type Stage = "upload" | "working" | "result";
type CategoryFilter = "all" | "shirt" | "top" | "dress";
type Result = { url: string; demo: boolean };

function Dialog({
  children,
  onClose,
  label,
  wide = false,
}: {
  children: ReactNode;
  onClose: () => void;
  label: string;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`dialog ${wide ? "dialog-wide" : ""}`}
      aria-label={label}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <button
        className="close-button icon-button"
        onClick={onClose}
        aria-label="Close dialog"
      >
        <X size={21} />
      </button>
      {children}
    </dialog>
  );
}

function SampleImage({ original = false }: { original?: boolean }) {
  return (
    <div className={`sample-panel ${original ? "sample-original" : ""}`}>
      <img
        src="/tryon-example.png"
        alt={
          original
            ? "Portrait from the supplied project example"
            : "Cardigan try-on reference from the supplied project example"
        }
      />
    </div>
  );
}

function getSaved(): string[] {
  try {
    const value: unknown = JSON.parse(
      localStorage.getItem("vyumi-saved") || "[]",
    );
    return Array.isArray(value)
      ? value.filter((id): id is string => typeof id === "string")
      : [];
  } catch {
    return [];
  }
}

export default function App() {
  const [demo, setDemo] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [catalogState, setCatalogState] = useState<
    "loading" | "ready" | "error"
  >("loading");
  const [reload, setReload] = useState(0);
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("curated");
  const [saved, setSaved] = useState<string[]>(getSaved);
  const [savedOnly, setSavedOnly] = useState(false);
  const [info, setInfo] = useState<"how" | "about" | null>(null);
  const [menu, setMenu] = useState(false);
  const [selected, setSelected] = useState<Product | null>(null);
  const [stage, setStage] = useState<Stage>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [photoUrl, setPhotoUrl] = useState("");
  const [useSample, setUseSample] = useState(false);
  const [validating, setValidating] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [viewOriginal, setViewOriginal] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [toast, setToast] = useState("");
  const task = useRef<AbortController | null>(null);
  const photoTask = useRef(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    setCatalogState("loading");
    setHealth(null);
    if (demo) {
      setProducts(demoProducts);
      setCatalogState("ready");
      return () => controller.abort();
    }
    Promise.allSettled([
      api.products(controller.signal),
      api.health(controller.signal),
    ]).then(([catalog, status]) => {
      if (controller.signal.aborted) return;
      if (catalog.status === "fulfilled") {
        setProducts(catalog.value);
        setCatalogState("ready");
      } else {
        setProducts([]);
        setCatalogState("error");
      }
      if (status.status === "fulfilled") setHealth(status.value);
    });
    return () => controller.abort();
  }, [demo, reload]);

  useEffect(() => {
    try {
      localStorage.setItem("vyumi-saved", JSON.stringify(saved));
    } catch {
      /* Saving in memory still works with storage disabled. */
    }
  }, [saved]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3200);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(
    () => () => {
      if (photoUrl) URL.revokeObjectURL(photoUrl);
    },
    [photoUrl],
  );
  useEffect(
    () => () => {
      task.current?.abort();
      photoTask.current++;
    },
    [],
  );

  const toggleSaved = (product: Product) => {
    const exists = saved.includes(product.id);
    setSaved((current) =>
      exists
        ? current.filter((id) => id !== product.id)
        : [...current, product.id],
    );
    setToast(
      exists ? "Removed from your saved pieces" : "Added to your saved pieces",
    );
  };
  const scrollToCollection = () => {
    setMenu(false);
    document
      .getElementById("collection")
      ?.scrollIntoView({ behavior: "smooth" });
  };
  const closeStudio = () => {
    task.current?.abort();
    photoTask.current++;
    setSelected(null);
    setValidating(false);
    setError("");
  };
  const openStudio = (product: Product) => {
    task.current?.abort();
    photoTask.current++;
    setSelected(product);
    setStage("upload");
    setError("");
    setResult(null);
    setViewOriginal(false);
  };
  const changeMode = () => {
    closeStudio();
    setDemo((current) => !current);
    setToast(
      demo ? "Connected mode selected" : "Demo mode · reference images only",
    );
  };

  async function chooseFile(candidate?: File) {
    if (!candidate) return;
    const version = ++photoTask.current;
    setError("");
    setValidating(true);
    try {
      if (!["image/jpeg", "image/png", "image/webp"].includes(candidate.type))
        throw new Error("Choose a JPEG, PNG, or WebP image.");
      if (candidate.size > 10 * 1024 * 1024)
        throw new Error(
          "This photo is larger than 10 MB. Please choose a smaller image.",
        );
      if (!candidate.size)
        throw new Error("This file is empty. Please choose another photo.");
      let bitmap: ImageBitmap;
      try {
        bitmap = await createImageBitmap(candidate);
      } catch {
        throw new Error(
          "This image couldn’t be read. Please try another photo.",
        );
      }
      const minimum = Math.min(bitmap.width, bitmap.height);
      bitmap.close();
      if (minimum < 512)
        throw new Error(
          "Your photo needs to be at least 512 pixels on its shortest side.",
        );
      if (version !== photoTask.current) return;
      setFile(candidate);
      setUseSample(false);
      setPhotoUrl(URL.createObjectURL(candidate));
    } catch (err) {
      if (version === photoTask.current) setError((err as Error).message);
    } finally {
      if (version === photoTask.current) setValidating(false);
      if (input.current) input.current.value = "";
    }
  }

  async function generate() {
    if (!selected || (!file && !useSample)) return;
    if (!demo && !health?.engine_ready) {
      setError(
        "Try-on generation is currently unavailable. You can use Demo mode to explore a reference result.",
      );
      return;
    }
    task.current?.abort();
    const controller = new AbortController();
    task.current = controller;
    const signal = controller.signal;
    setStage("working");
    setError("");
    setViewOriginal(false);
    try {
      if (demo) {
        for (const message of [
          "Preparing your studio…",
          "Exploring the styling workflow…",
          "Opening the reference example…",
        ]) {
          setProgress(message);
          await wait(650, signal);
        }
        setResult({ url: "/tryon-example.png", demo: true });
      } else {
        setProgress("Uploading your photo…");
        const uploaded = await api.upload(file!, signal);
        setProgress("Joining the styling queue…");
        const job = await api.generate(
          uploaded.user_image_id,
          selected.id,
          signal,
        );
        const deadline = Date.now() + 5 * 60_000;
        let finalUrl = "";
        while (Date.now() < deadline) {
          const status = await api.job(job.job_id, signal);
          if (status.status === "completed") {
            finalUrl = assetUrl(status.result_image_url);
            break;
          }
          if (status.status === "failed")
            throw new Error(
              status.message ||
                "Generation failed. Please try a different image.",
            );
          setProgress(
            status.status === "processing"
              ? "Creating your look…"
              : "Your look is in the queue…",
          );
          await wait(1800, signal);
        }
        if (!finalUrl)
          throw new Error(
            "This is taking longer than expected. Please try again in a few minutes.",
          );
        setResult({ url: finalUrl, demo: false });
      }
      if (!signal.aborted) setStage("result");
    } catch (err) {
      if (!signal.aborted) {
        setError((err as Error).message);
        setStage("upload");
      }
    }
  }

  async function download() {
    if (!result || !selected) return;
    setDownloading(true);
    setError("");
    const controller = new AbortController();
    task.current = controller;
    try {
      const response = await fetch(result.url, {
        signal: AbortSignal.any([
          controller.signal,
          AbortSignal.timeout(30_000),
        ]),
      });
      if (!response.ok)
        throw new Error("The image could not be downloaded. Please try again.");
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = result.demo
        ? "vyumi-reference-sheet.png"
        : `vyumi-${selected.id}.png`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      if (!controller.signal.aborted)
        setToast(
          result.demo
            ? "Reference sheet downloaded"
            : "Your look has been downloaded",
        );
    } catch (err) {
      if (!controller.signal.aborted) setError((err as Error).message);
    } finally {
      setDownloading(false);
    }
  }

  let visible = products.filter(
    (product) =>
      (category === "all" || product.category === category) &&
      (!savedOnly || saved.includes(product.id)) &&
      `${product.name} ${product.category} ${product.description}`
        .toLowerCase()
        .includes(query.toLowerCase().trim()),
  );
  if (sort === "name")
    visible = [...visible].sort((a, b) => a.name.localeCompare(b.name));
  if (sort === "category")
    visible = [...visible].sort((a, b) => a.category.localeCompare(b.category));
  const connected = !demo && catalogState === "ready";
  const photoPresent = !!file || useSample;

  return (
    <>
      <div
        className="announcement"
        role="region"
        aria-label="Studio announcement"
      >
        <span>A little curiosity. A whole new look.</span>
        <span className="announcement-right">
          YOUR PERSONAL STYLE STUDIO <Sparkles size={12} />
        </span>
      </div>
      <header className="header page-width">
        <a href="#" className="wordmark" aria-label="VYUMI home">
          VYUMI<span>®</span>
        </a>
        <nav
          className={menu ? "nav nav-open" : "nav"}
          aria-label="Main navigation"
        >
          <button
            className={!savedOnly ? "nav-active" : ""}
            onClick={() => {
              setSavedOnly(false);
              scrollToCollection();
            }}
          >
            Style studio
          </button>
          <button
            onClick={() => {
              setInfo("how");
              setMenu(false);
            }}
          >
            How it works
          </button>
          <button
            onClick={() => {
              setInfo("about");
              setMenu(false);
            }}
          >
            About VYUMI
          </button>
        </nav>
        <div className="header-actions">
          <button
            className={`saved-nav ${savedOnly ? "active" : ""}`}
            onClick={() => {
              setSavedOnly((current) => !current);
              scrollToCollection();
            }}
            aria-label={`Saved${saved.length} pieces`}
          >
            <Heart size={18} />
            <span>Saved</span>
            <b>{saved.length}</b>
          </button>
          <button
            className="mobile-menu icon-button"
            aria-label="Toggle navigation"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            {menu ? <X size={21} /> : <Menu size={21} />}
          </button>
        </div>
      </header>

      <main>
        <section className="hero page-width" aria-labelledby="hero-title">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="small-line" /> A NEW WAY TO FIND YOURSELF
            </div>
            <h1 id="hero-title">
              Your style.
              <br />
              Your{" "}
              <span className="italic-word">
                way.
                <svg viewBox="0 0 230 22" aria-hidden="true">
                  <path d="M4 14Q111-2 222 10M20 21Q125 5 206 17" />
                </svg>
              </span>
            </h1>
            <p>
              A new look, without the guesswork. Discover pieces
              <br className="desktop-break" /> you love and see how they look on{" "}
              <em>you.</em>
            </p>
            <div className="hero-actions">
              <button
                className="button button-dark"
                onClick={scrollToCollection}
              >
                Find your next look <ArrowUpRight size={19} />
              </button>
              <button className="text-button" onClick={() => setInfo("how")}>
                How it works <ArrowRight size={16} />
              </button>
            </div>
            <div className="hero-proof">
              <span className="proof-icon">
                <CheckCheck size={19} />
              </span>
              <span>Your photo. Your pick. A whole new possibility.</span>
            </div>
            <div className="hero-index">
              <span>01 / THE STYLE STUDIO</span>
              <span>
                MADE FOR THE WAY YOU ARE <ArrowDown size={12} />
              </span>
            </div>
          </div>
          <div className="hero-visual">
            <div className="hero-orbit" />
            <span className="visual-label">THE NEXT LOOK IS YOURS.</span>
            <div className="hero-model">
              <SampleImage />
              <div className="model-caption">
                <span>THE VYUMI TRY-ON EDIT</span>
                <ArrowUpRight size={17} />
              </div>
            </div>
            <div className="floating-card">
              <span>FROM THE COLLECTION</span>
              <Garment product={demoProducts[0]} />
              <div>
                <b>Less wondering.</b>
                <br />
                <i>More wearing.</i>
              </div>
            </div>
            <div className="hero-sticker">
              <Sparkles size={24} />
              <span>
                A LITTLE
                <br />
                STYLE MAGIC
              </span>
            </div>
            <span className="sample-credit">
              PROJECT REFERENCE IMAGE · ILLUSTRATIVE STYLING
            </span>
          </div>
        </section>

        <div className="value-strip">
          <div className="page-width">
            <span>
              <Sparkles size={17} /> A fitting room, reimagined
            </span>
            <span>
              <ImagePlus size={17} /> Made personal with your photo
            </span>
            <span>
              <ShieldCheck size={17} /> Explore at your own pace
            </span>
            <span className="strip-signature">GOOD STYLE STARTS WITH YOU.</span>
          </div>
        </div>

        <section
          className="collection page-width"
          id="collection"
          aria-labelledby="collection-title"
        >
          <div className="section-top">
            <div>
              <div className="eyebrow">
                THE CURATED COLLECTION{" "}
                <span className="tiny-pill">VOL. 01</span>
              </div>
              <h2 id="collection-title">
                {savedOnly ? "Your saved pieces." : "Meet your next look."}
                <span className="orange-dot">.</span>
              </h2>
              <p>
                {savedOnly
                  ? "A little collection of the things that caught your eye."
                  : "Everyday favorites. Statement pieces. Something that feels like you."}
              </p>
            </div>
            <div className="mode-control">
              <span className={`connection-dot ${connected ? "online" : ""}`} />
              <span>
                {demo
                  ? "Demo collection"
                  : catalogState === "loading"
                    ? "Connecting…"
                    : connected
                      ? "Live collection"
                      : "Studio offline"}
              </span>
              <button
                role="switch"
                aria-checked={demo}
                aria-label="Demo mode"
                className={`switch ${demo ? "on" : ""}`}
                onClick={changeMode}
              >
                <span />
              </button>
              <span>Demo</span>
            </div>
          </div>

          {(demo || (connected && !health?.engine_ready)) && (
            <div className="studio-notice">
              <Sparkles size={16} />
              <span>
                {demo
                  ? "You’re exploring Demo mode. Try-on results use a labeled reference image, not your uploaded photo."
                  : "The collection is live. Virtual try-on is currently offline; switch on Demo to explore the experience."}
              </span>
            </div>
          )}

          <div className="catalog-toolbar">
            <div className="category-tabs" aria-label="Filter by category">
              {(
                [
                  ["all", "All pieces"],
                  ["shirt", "Shirts"],
                  ["top", "Tops"],
                  ["dress", "Dresses"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id}
                  aria-pressed={category === id}
                  className={category === id ? "selected" : ""}
                  onClick={() => setCategory(id)}
                >
                  {label}
                  <span>
                    {
                      products.filter(
                        (p) =>
                          (id === "all" || p.category === id) &&
                          (!savedOnly || saved.includes(p.id)),
                      ).length
                    }
                  </span>
                </button>
              ))}
            </div>
            <div className="catalog-tools">
              <label className="search-field">
                <Search size={16} />
                <input
                  aria-label="Search pieces"
                  placeholder="Find a piece…"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
                {query && (
                  <button
                    aria-label="Clear search"
                    onClick={() => setQuery("")}
                  >
                    <X size={14} />
                  </button>
                )}
              </label>
              <label className="sort-field">
                <SlidersHorizontal size={15} />
                <select
                  aria-label="Sort pieces"
                  value={sort}
                  onChange={(event) => setSort(event.target.value)}
                >
                  <option value="curated">Curated order</option>
                  <option value="name">Name: A–Z</option>
                  <option value="category">By category</option>
                </select>
                <ChevronDown size={14} />
              </label>
            </div>
          </div>

          <div className="catalog-meta">
            <span>
              {catalogState === "loading"
                ? "FINDING YOUR FAVORITES…"
                : `${visible.length} PIECES TO MAKE YOUR OWN`}
            </span>
            {savedOnly ? (
              <button onClick={() => setSavedOnly(false)}>
                View all pieces <ArrowRight size={13} />
              </button>
            ) : (
              <span>
                SELECT A PIECE. MAKE IT PERSONAL. <ArrowDown size={12} />
              </span>
            )}
          </div>

          {catalogState === "error" ? (
            <div className="empty-state">
              <RefreshCw size={30} />
              <h3>The studio is taking a moment.</h3>
              <p>
                We couldn’t reach the collection. Reconnect to the backend, or
                explore the sample collection in Demo mode.
              </p>
              <div>
                <button
                  className="button button-dark"
                  onClick={() => setReload((current) => current + 1)}
                >
                  Try again <RefreshCw size={16} />
                </button>
                <button
                  className="button button-outline"
                  onClick={() => setDemo(true)}
                >
                  Explore demo <ArrowRight size={16} />
                </button>
              </div>
            </div>
          ) : catalogState === "loading" ? (
            <div
              className="product-grid"
              aria-label="Loading collection"
              aria-busy="true"
            >
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div className="skeleton-card" key={i}>
                  <div />
                  <span />
                  <span />
                </div>
              ))}
            </div>
          ) : visible.length === 0 ? (
            <div className="empty-state">
              <Search size={30} />
              <h3>
                {savedOnly && !saved.length
                  ? "Keep a little inspiration."
                  : "No pieces found just yet."}
              </h3>
              <p>
                {savedOnly && !saved.length
                  ? "Tap the heart on a piece to save it here for later."
                  : "Try another search or explore the rest of the collection."}
              </p>
              <button
                className="button button-dark"
                onClick={() => {
                  setQuery("");
                  setCategory("all");
                  setSavedOnly(false);
                }}
              >
                Explore all pieces <ArrowRight size={16} />
              </button>
            </div>
          ) : (
            <div className="product-grid">
              {visible.map((product, index) => (
                <article
                  className="product-card"
                  key={product.id}
                  style={
                    {
                      "--card-bg": palette[product.id]?.background || "#e9e7df",
                      "--card-index": index,
                    } as React.CSSProperties
                  }
                >
                  <div className="product-art">
                    <span className="product-tag">
                      {palette[product.id]?.note || "The curated edit"}
                    </span>
                    <button
                      className={`favorite-button ${saved.includes(product.id) ? "is-saved" : ""}`}
                      aria-label={`${saved.includes(product.id) ? "Unsave" : "Save"} ${product.name}`}
                      aria-pressed={saved.includes(product.id)}
                      onClick={() => toggleSaved(product)}
                    >
                      <Heart
                        size={18}
                        fill={
                          saved.includes(product.id) ? "currentColor" : "none"
                        }
                      />
                    </button>
                    <button
                      className="garment-button"
                      onClick={() => openStudio(product)}
                      aria-label={`Try on ${product.name}`}
                    >
                      <Garment product={product} />
                    </button>
                    <span className="art-caption">GARMENT ILLUSTRATION</span>
                    <button
                      className="art-cta"
                      onClick={() => openStudio(product)}
                    >
                      Make it yours <ArrowUpRight size={15} />
                    </button>
                  </div>
                  <div className="product-details">
                    <div>
                      <span className="product-category">
                        {product.category === "shirt"
                          ? "THE SHIRT EDIT"
                          : product.category === "top"
                            ? "THE EVERYDAY TOP"
                            : "THE DRESS EDIT"}
                      </span>
                      <h3>
                        <button onClick={() => openStudio(product)}>
                          {product.name}
                        </button>
                      </h3>
                    </div>
                    <span
                      className="swatch"
                      style={{
                        background: palette[product.id]?.color || "#a7b29b",
                      }}
                    />
                  </div>
                  <div className="product-bottom">
                    <span>
                      {product.category === "dress"
                        ? "A whole new mood"
                        : "An everyday kind of favorite"}
                    </span>
                    <button
                      onClick={() => openStudio(product)}
                      aria-label={`Open ${product.name}`}
                    >
                      <ArrowUpRight size={19} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
          <p className="collection-footnote">
            <span /> Thoughtfully curated. Endlessly you. <span />
          </p>
        </section>

        <section className="how-section page-width" aria-labelledby="how-title">
          <div className="how-intro">
            <div className="eyebrow">A LITTLE LESS GUESSWORK</div>
            <h2 id="how-title">
              From <i>what if</i>
              <br />
              to <i>that’s me.</i>
            </h2>
            <button className="text-button" onClick={() => setInfo("how")}>
              A peek inside the studio <ArrowUpRight size={17} />
            </button>
          </div>
          <div className="how-steps">
            {[
              [
                ImagePlus,
                "01",
                "Bring yourself.",
                "Upload a clear, well-lit photo. The best starting point is you.",
              ],
              [
                Heart,
                "02",
                "Find your piece.",
                "Pick something familiar. Or something a little unexpected.",
              ],
              [
                Sparkles,
                "03",
                "See the possibility.",
                "Create a virtual try-on, then keep the looks you love.",
              ],
            ].map(([Icon, number, title, copy]) => {
              const StepIcon = Icon as typeof Heart;
              return (
                <div className="how-step" key={String(number)}>
                  <div className="step-top">
                    <StepIcon size={23} />
                    <span>{String(number)}</span>
                  </div>
                  <h3>{String(title)}</h3>
                  <p>{String(copy)}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section className="closing-note page-width">
          <span className="closing-star" aria-hidden="true">
            ✳︎
          </span>
          <p>
            Style is personal.
            <br />
            <i>Finding it should be, too.</i>
          </p>
          <button
            className="round-link"
            onClick={scrollToCollection}
            aria-label="Back to collection"
          >
            <ArrowUpRight size={28} />
          </button>
        </section>
      </main>

      <footer className="footer page-width">
        <div>
          <a href="#" className="wordmark">
            VYUMI<span>®</span>
          </a>
          <p>Style it your way.</p>
        </div>
        <div className="footer-center">
          <span>AN EXPERIMENT IN PERSONAL STYLE.</span>
          <span>Internal research prototype · Non-commercial</span>
        </div>
        <button className="text-button" onClick={() => setInfo("about")}>
          A note on this project <ArrowUpRight size={15} />
        </button>
      </footer>
      <div className="toast" role="status" aria-live="polite">
        {toast && (
          <span>
            <Check size={16} />
            {toast}
          </span>
        )}
      </div>

      {info && (
        <Dialog
          label={info === "how" ? "How VYUMI works" : "About VYUMI"}
          onClose={() => setInfo(null)}
        >
          <div className="info-content">
            <span className="eyebrow">WELCOME TO YOUR STYLE STUDIO</span>
            <h2>
              {info === "how" ? (
                <>
                  A new look.
                  <br />
                  <i>In three little steps.</i>
                </>
              ) : (
                <>
                  Made for curiosity.
                  <br />
                  <i>Made for you.</i>
                </>
              )}
            </h2>
            {info === "how" ? (
              <>
                <ol className="instruction-list">
                  <li>
                    <span>01</span>
                    <div>
                      <h3>Choose a piece</h3>
                      <p>
                        Browse shirts, tops, and dresses. Save favorites with
                        the heart, or select one to try on.
                      </p>
                    </div>
                  </li>
                  <li>
                    <span>02</span>
                    <div>
                      <h3>Add your photo</h3>
                      <p>
                        Use a clear, well-lit, front-facing photo with one
                        person and a visible torso. JPEG, PNG, or WebP; up to 10
                        MB; at least 512 px on the shortest side.
                      </p>
                    </div>
                  </li>
                  <li>
                    <span>03</span>
                    <div>
                      <h3>Explore your look</h3>
                      <p>
                        When the try-on service is available, we’ll generate a
                        new image. Compare it with your original and download
                        the result.
                      </p>
                    </div>
                  </li>
                </ol>
                <div className="soft-note">
                  <Sparkles size={18} />
                  <p>
                    Demo mode works without the try-on service. It shows a
                    clearly labeled project reference, never a generated result
                    of your photo.
                  </p>
                </div>
              </>
            ) : (
              <>
                <p className="info-paragraph">
                  VYUMI is an experimental virtual fitting room that puts a
                  little more possibility into finding your style. This edition
                  explores shirts, tops, and dresses.
                </p>
                <p className="info-paragraph">
                  Virtual try-on is a visual experiment, not a guarantee of size
                  or physical fit. Product artwork is illustrative; the current
                  catalog contains prototype garment assets.
                </p>
                <div className="soft-note">
                  <ShieldCheck size={20} />
                  <p>
                    In connected mode, photos are uploaded to the backend for
                    processing. Avoid sensitive images. In Demo mode your photo
                    stays in this browser tab. Saved pieces are stored on this
                    device.
                  </p>
                </div>
                <p className="license-note">
                  Internal, non-commercial research prototype. CatVTON models
                  are licensed CC BY-NC-SA 4.0. The reference image is supplied
                  with the original project.
                </p>
              </>
            )}
            <button
              className="button button-dark full-width"
              onClick={() => {
                setInfo(null);
                scrollToCollection();
              }}
            >
              Let’s find your next look <ArrowRight size={18} />
            </button>
          </div>
        </Dialog>
      )}

      {selected && (
        <Dialog label={`Try on ${selected.name}`} onClose={closeStudio} wide>
          <div className="studio-dialog">
            <div className="studio-sidebar">
              <span className="eyebrow">YOUR SELECTED PIECE</span>
              <div
                className="selected-art"
                style={{
                  background: palette[selected.id]?.background || "#e9e7df",
                }}
              >
                <Garment product={selected} />
                <span>GARMENT ILLUSTRATION</span>
              </div>
              <span className="product-category">
                {selected.category.toUpperCase()} / THE VYUMI EDIT
              </span>
              <h3>{selected.name}</h3>
              <p>{selected.description.replace(/\[.*?\]\s*/, "")}</p>
              {!demo && (
                <a
                  className="text-button"
                  href={assetUrl(
                    selected.image_url || `/products/${selected.id}/image`,
                  )}
                  target="_blank"
                  rel="noreferrer"
                >
                  View original garment asset <ArrowUpRight size={14} />
                </a>
              )}
              <div className="sidebar-bottom">
                <ShieldCheck size={17} />
                <p>
                  {demo
                    ? "Demo photos stay in this browser tab."
                    : "Your photo is sent to the connected try-on service."}
                </p>
              </div>
            </div>
            <div className="studio-main">
              <div className="studio-breadcrumb">
                <span className={stage === "upload" ? "current" : ""}>
                  01 YOUR PHOTO
                </span>
                <span className="breadcrumb-line" />
                <span className={stage !== "upload" ? "current" : ""}>
                  02 YOUR LOOK
                </span>
                {demo && <span className="demo-badge">DEMO</span>}
              </div>
              {stage === "upload" && (
                <>
                  <h2>
                    Make it <i>yours.</i>
                  </h2>
                  <p className="studio-description">
                    A little style exploration starts with your photo.
                  </p>
                  <input
                    ref={input}
                    className="sr-only"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(event) =>
                      void chooseFile(event.target.files?.[0])
                    }
                    aria-label="Upload portrait"
                  />
                  <div
                    className={`upload-area ${dragging ? "dragging" : ""} ${photoPresent ? "has-photo" : ""}`}
                    onDragOver={(event) => {
                      event.preventDefault();
                      setDragging(true);
                    }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={(event) => {
                      event.preventDefault();
                      setDragging(false);
                      void chooseFile(event.dataTransfer.files[0]);
                    }}
                  >
                    {photoPresent ? (
                      <>
                        <div className="photo-preview">
                          {useSample ? (
                            <SampleImage original />
                          ) : (
                            <img src={photoUrl} alt="Your uploaded portrait" />
                          )}
                        </div>
                        <div className="photo-ready">
                          <span>
                            <Check size={15} />{" "}
                            {useSample ? "Demo portrait selected" : file?.name}
                          </span>
                          <button
                            onClick={() => {
                              photoTask.current++;
                              setFile(null);
                              setPhotoUrl("");
                              setUseSample(false);
                              setError("");
                              setValidating(false);
                            }}
                            aria-label="Remove photo"
                          >
                            <X size={17} />
                          </button>
                        </div>
                      </>
                    ) : (
                      <button
                        className="upload-target"
                        onClick={() => input.current?.click()}
                        disabled={validating}
                      >
                        <span className="upload-icon">
                          {validating ? (
                            <LoaderCircle className="spin" size={25} />
                          ) : (
                            <Upload size={25} />
                          )}
                        </span>
                        <b>
                          {validating
                            ? "Checking your photo…"
                            : "Drop your photo here"}
                        </b>
                        <span>
                          or <u>browse files</u>
                        </span>
                        <small>JPEG, PNG, WebP · Max 10 MB · Min 512 px</small>
                      </button>
                    )}
                  </div>
                  {photoPresent && (
                    <button
                      className="text-button change-photo"
                      onClick={() => input.current?.click()}
                      disabled={validating}
                    >
                      {validating
                        ? "Checking photo…"
                        : "Choose a different photo"}{" "}
                      <RefreshCw size={13} />
                    </button>
                  )}
                  <div className="photo-tips">
                    <span>
                      <Check size={13} /> One person
                    </span>
                    <span>
                      <Check size={13} /> Good lighting
                    </span>
                    <span>
                      <Check size={13} /> Visible torso
                    </span>
                  </div>
                  {demo && !photoPresent && (
                    <button
                      className="sample-button"
                      onClick={() => {
                        photoTask.current++;
                        setUseSample(true);
                        setFile(null);
                        setPhotoUrl("");
                        setError("");
                        setValidating(false);
                      }}
                    >
                      <ImagePlus size={17} /> Just exploring? Use a demo
                      portrait <ArrowRight size={15} />
                    </button>
                  )}
                  {error && (
                    <div className="error-message" role="alert">
                      {error}
                    </div>
                  )}
                  {!demo && !health?.engine_ready && (
                    <div className="soft-note engine-note">
                      <Sparkles size={17} />
                      <p>
                        Virtual try-on is currently offline.{" "}
                        <button
                          onClick={() => {
                            closeStudio();
                            setDemo(true);
                            setToast(
                              "Demo mode is on. Choose a piece to continue.",
                            );
                          }}
                        >
                          Explore Demo mode
                        </button>{" "}
                        to see the workflow.
                      </p>
                    </div>
                  )}
                  <button
                    className="button button-orange full-width generate-button"
                    disabled={
                      !photoPresent ||
                      validating ||
                      (!demo && !health?.engine_ready)
                    }
                    onClick={() => void generate()}
                  >
                    {demo ? "Explore a reference look" : "Create my look"}{" "}
                    <Sparkles size={17} />
                  </button>
                  <p className="small-disclaimer">
                    {demo
                      ? "Demo shows a project sample, not a transformation of your photo."
                      : "A visual preview, not a guarantee of size or fit."}
                  </p>
                </>
              )}
              {stage === "working" && (
                <div className="working-state" role="status" aria-live="polite">
                  <div className="working-art">
                    <Garment product={selected} />
                    <span className="scan-line" />
                  </div>
                  <span className="loading-label">
                    <LoaderCircle size={16} className="spin" />
                    {demo ? "EXPLORING DEMO" : "YOUR STYLE IS IN THE MAKING"}
                  </span>
                  <h2>
                    {demo ? (
                      <>
                        A little <i>inspiration.</i>
                      </>
                    ) : (
                      <>
                        Something <i>you.</i>
                      </>
                    )}
                  </h2>
                  <p>{progress}</p>
                  <span className="working-track" />
                  <small>
                    {demo
                      ? "Opening a reference from the original project."
                      : "Good things take a moment. You can leave this open while we work."}
                  </small>
                  <button
                    className="text-button"
                    onClick={() => {
                      task.current?.abort();
                      setStage("upload");
                      setError("");
                    }}
                  >
                    Cancel {demo ? "demo" : "waiting"} <X size={14} />
                  </button>
                  {!demo && (
                    <small>
                      Closing this window stops polling; a submitted server job
                      may continue.
                    </small>
                  )}
                </div>
              )}
              {stage === "result" && result && (
                <>
                  <span className="result-kicker">
                    <CheckCheck size={17} />
                    {result.demo
                      ? "YOUR REFERENCE IS READY"
                      : "YOUR LOOK IS READY"}
                  </span>
                  <h2>
                    {result.demo ? (
                      <>
                        See the <i>possibility.</i>
                      </>
                    ) : (
                      <>
                        Hello, <i>new you.</i>
                      </>
                    )}
                  </h2>
                  <p className="studio-description">
                    {result.demo
                      ? "An example from the original VYUMI project."
                      : "A new perspective on your personal style."}
                  </p>
                  <div className="result-tabs">
                    <button
                      aria-pressed={viewOriginal}
                      className={viewOriginal ? "active" : ""}
                      onClick={() => setViewOriginal(true)}
                    >
                      {useSample ? "Demo portrait" : "Your photo"}
                    </button>
                    <button
                      aria-pressed={!viewOriginal}
                      className={!viewOriginal ? "active" : ""}
                      onClick={() => setViewOriginal(false)}
                    >
                      {result.demo ? "Reference result" : "Your new look"}
                    </button>
                  </div>
                  <div className="result-image">
                    {viewOriginal ? (
                      useSample ? (
                        <SampleImage original />
                      ) : (
                        <img
                          src={photoUrl}
                          alt="Your original uploaded portrait"
                        />
                      )
                    ) : result.demo ? (
                      <SampleImage />
                    ) : (
                      <img
                        src={result.url}
                        alt={`Your generated try-on wearing ${selected.name}`}
                        onError={() =>
                          setError(
                            "The result image couldn’t be loaded. Please try downloading it or create a new look.",
                          )
                        }
                      />
                    )}
                    <span className="image-label">
                      {viewOriginal
                        ? useSample
                          ? "DEMO PORTRAIT"
                          : "ORIGINAL PHOTO"
                        : result.demo
                          ? "REFERENCE SAMPLE"
                          : "VYUMI TRY-ON"}
                    </span>
                  </div>
                  {result.demo && (
                    <p className="demo-result-note">
                      This reference is not generated from your photo or
                      selected garment.
                    </p>
                  )}
                  {error && (
                    <div className="error-message" role="alert">
                      {error}
                    </div>
                  )}
                  <button
                    className="button button-orange full-width"
                    onClick={() => void download()}
                    disabled={downloading}
                  >
                    {downloading ? (
                      <LoaderCircle className="spin" size={17} />
                    ) : (
                      <Download size={17} />
                    )}{" "}
                    {result.demo
                      ? "Download reference sheet"
                      : "Download my look"}
                  </button>
                  <div className="result-actions">
                    <button className="text-button" onClick={closeStudio}>
                      <ArrowLeft size={15} /> Try another piece
                    </button>
                    <button
                      className="text-button"
                      onClick={() => {
                        setStage("upload");
                        setError("");
                      }}
                    >
                      Change photo <RefreshCw size={14} />
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </Dialog>
      )}
    </>
  );
}
