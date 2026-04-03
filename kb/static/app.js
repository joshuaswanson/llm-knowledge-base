(function () {
  "use strict";

  var state = {
    articles: [],
    chatHistory: [],
    currentView: "dashboard",
    graphRendered: false,
  };

  // ---- Helpers ----

  async function api(path, options) {
    var res = await fetch(path, options);
    if (!res.ok) {
      var text = await res.text();
      throw new Error(text || res.statusText);
    }
    return res.json();
  }

  function $(sel) {
    return document.querySelector(sel);
  }

  function $$(sel) {
    return document.querySelectorAll(sel);
  }

  function formatNumber(n) {
    if (n === undefined || n === null) return "--";
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return String(n);
  }

  function showFeedback(msg, type) {
    var el = $("#action-feedback");
    el.textContent = msg;
    el.className = "action-feedback " + type;
    if (type !== "loading") {
      setTimeout(function () {
        el.classList.add("hidden");
      }, 5000);
    }
  }

  function renderMarkdown(md) {
    var withLinks = md.replace(
      /\[\[([^\]]+)\]\]/g,
      '<span class="wikilink" data-target="$1">$1</span>',
    );
    return marked.parse(withLinks);
  }

  // ---- Navigation ----

  function switchView(viewName) {
    state.currentView = viewName;
    $$(".view").forEach(function (v) {
      v.classList.remove("active");
    });
    $$(".nav-item").forEach(function (n) {
      n.classList.remove("active");
    });
    var view = $("#view-" + viewName);
    if (view) view.classList.add("active");
    var nav = document.querySelector('.nav-item[data-view="' + viewName + '"]');
    if (nav) nav.classList.add("active");

    if (viewName === "dashboard") loadDashboard();
    if (viewName === "browse") loadBrowse();
    if (viewName === "graph") loadGraph();
  }

  $$(".nav-item").forEach(function (item) {
    item.addEventListener("click", function () {
      switchView(this.dataset.view);
    });
  });

  // ---- Dashboard ----

  async function loadDashboard() {
    try {
      var status = await api("/api/status");
      $("#stat-sources").textContent = formatNumber(status.sources);
      $("#stat-concepts").textContent = formatNumber(status.concepts);
      $("#stat-words").textContent = formatNumber(status.total_words);
    } catch (e) {
      console.error("Failed to load status:", e);
    }

    try {
      state.articles = await api("/api/articles");
      var list = $("#recent-list");
      if (!state.articles.length) {
        list.innerHTML =
          '<div class="loading-placeholder">No articles yet. Ingest a URL to get started.</div>';
        return;
      }
      var recent = state.articles.slice(0, 10);
      list.innerHTML = recent
        .map(function (a) {
          return (
            '<div class="article-list-item" data-path="' +
            a.path +
            '">' +
            '<span class="title">' +
            a.title +
            "</span>" +
            '<span class="meta">' +
            a.group +
            " &middot; " +
            formatNumber(a.words) +
            " words</span>" +
            "</div>"
          );
        })
        .join("");
      list.querySelectorAll(".article-list-item").forEach(function (el) {
        el.addEventListener("click", function () {
          switchView("browse");
          setTimeout(function () {
            openArticle(el.dataset.path);
          }, 50);
        });
      });
    } catch (e) {
      console.error("Failed to load articles:", e);
    }
  }

  // Ingest
  $("#btn-ingest").addEventListener("click", async function () {
    var url = $("#ingest-url").value.trim();
    if (!url) return;
    var btn = $("#btn-ingest");
    btn.disabled = true;
    showFeedback("Ingesting...", "loading");
    try {
      await api("/api/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url }),
      });
      showFeedback("Successfully ingested: " + url, "success");
      $("#ingest-url").value = "";
      loadDashboard();
    } catch (e) {
      showFeedback("Ingest failed: " + e.message, "error");
    } finally {
      btn.disabled = false;
    }
  });

  // Compile
  $("#btn-compile").addEventListener("click", async function () {
    var btn = $("#btn-compile");
    btn.disabled = true;
    showFeedback("Compiling knowledge...", "loading");
    try {
      var result = await api("/api/compile", { method: "POST" });
      showFeedback(
        "Done: " +
          result.sources_compiled +
          " sources compiled, " +
          result.concepts_created +
          " concepts created.",
        "success",
      );
      loadDashboard();
    } catch (e) {
      showFeedback("Compile failed: " + e.message, "error");
    } finally {
      btn.disabled = false;
    }
  });

  // ---- Browse ----

  async function loadBrowse() {
    if (!state.articles.length) {
      state.articles = await api("/api/articles");
    }
    var concepts = state.articles.filter(function (a) {
      return a.group === "concept";
    });
    var sources = state.articles.filter(function (a) {
      return a.group === "source";
    });

    renderBrowseGroup("#browse-concepts .browse-list", concepts);
    renderBrowseGroup("#browse-sources .browse-list", sources);
  }

  function renderBrowseGroup(selector, articles) {
    var ul = $(selector);
    ul.innerHTML = articles
      .map(function (a) {
        return (
          '<li data-path="' +
          a.path +
          '"><span class="browse-title">' +
          a.title +
          "</span>" +
          (a.tags && a.tags.length
            ? '<span class="browse-tags">' +
              a.tags
                .map(function (t) {
                  return '<span class="tag-pill">' + t + "</span>";
                })
                .join("") +
              "</span>"
            : "") +
          "</li>"
        );
      })
      .join("");
    ul.querySelectorAll("li").forEach(function (li) {
      li.addEventListener("click", function () {
        openArticle(li.dataset.path);
        $$(".browse-list li").forEach(function (el) {
          el.classList.remove("active");
        });
        li.classList.add("active");
      });
    });
  }

  async function openArticle(path) {
    var content = $("#browse-content");
    content.innerHTML = '<div class="loading-placeholder">Loading...</div>';
    try {
      var data = await api("/api/article/" + encodeURIComponent(path));
      var tags = data.tags || [];
      var group = path.startsWith("concepts/") ? "concept" : "source";

      var html = '<div class="article-meta">';
      html += "<h1>" + data.title + "</h1>";
      if (tags.length) {
        html += '<div class="article-tags">';
        tags.forEach(function (t) {
          html += '<span class="tag-pill ' + group + '">' + t + "</span>";
        });
        html += "</div>";
      }
      if (data.words) {
        html +=
          '<div class="article-words">' +
          formatNumber(data.words) +
          " words</div>";
      }
      html += "</div>";
      html +=
        '<div class="article-body">' + renderMarkdown(data.markdown) + "</div>";

      content.innerHTML = html;

      // Wire up wikilinks
      content.querySelectorAll(".wikilink").forEach(function (el) {
        el.addEventListener("click", function () {
          var target = el.dataset.target;
          var match = state.articles.find(function (a) {
            return (
              a.title.toLowerCase() === target.toLowerCase() ||
              a.path
                .toLowerCase()
                .includes(target.toLowerCase().replace(/\s+/g, "-"))
            );
          });
          if (match) {
            openArticle(match.path);
          }
        });
      });
    } catch (e) {
      content.innerHTML =
        '<div class="loading-placeholder">Failed to load article.</div>';
    }
  }

  // ---- Search ----

  async function doSearch() {
    var q = $("#search-input").value.trim();
    if (!q) return;
    var results = $("#search-results");
    results.innerHTML = '<div class="loading-placeholder">Searching...</div>';
    try {
      var items = await api("/api/search?q=" + encodeURIComponent(q));
      if (!items.length) {
        results.innerHTML =
          '<div class="loading-placeholder">No results found.</div>';
        return;
      }
      results.innerHTML = items
        .map(function (r) {
          return (
            '<div class="search-result" data-path="' +
            r.path +
            '">' +
            '<div class="result-title">' +
            r.title +
            "</div>" +
            '<div class="result-score">Score: ' +
            Number(r.score).toFixed(3) +
            "</div>" +
            '<div class="result-snippet">' +
            (r.snippet || "") +
            "</div>" +
            "</div>"
          );
        })
        .join("");
      results.querySelectorAll(".search-result").forEach(function (el) {
        el.addEventListener("click", function () {
          switchView("browse");
          setTimeout(function () {
            openArticle(el.dataset.path);
          }, 50);
        });
      });
    } catch (e) {
      results.innerHTML =
        '<div class="loading-placeholder">Search failed: ' +
        e.message +
        "</div>";
    }
  }

  $("#btn-search").addEventListener("click", doSearch);
  $("#search-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter") doSearch();
  });

  // ---- Chat ----

  function appendChatMessage(role, content) {
    var messages = $("#chat-messages");
    var welcome = messages.querySelector(".chat-welcome");
    if (welcome) welcome.remove();

    var bubble = document.createElement("div");
    bubble.className = "chat-bubble " + role;

    if (role === "assistant" && content) {
      bubble.innerHTML = renderMarkdown(content);
    } else if (content) {
      bubble.textContent = content;
    }

    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  async function sendChat() {
    var input = $("#chat-input");
    var q = input.value.trim();
    if (!q) return;
    input.value = "";

    appendChatMessage("user", q);
    state.chatHistory.push({ role: "user", content: q });

    var loadingBubble = appendChatMessage("assistant", "");
    loadingBubble.classList.add("loading");
    loadingBubble.textContent = "Thinking...";

    try {
      var data = await api("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      var answer = data.answer || "No response.";
      loadingBubble.classList.remove("loading");
      loadingBubble.innerHTML = renderMarkdown(answer);
      state.chatHistory.push({ role: "assistant", content: answer });
    } catch (e) {
      loadingBubble.classList.remove("loading");
      loadingBubble.textContent = "Error: " + e.message;
    }
    $("#chat-messages").scrollTop = $("#chat-messages").scrollHeight;
  }

  $("#btn-chat-send").addEventListener("click", sendChat);
  $("#chat-input").addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendChat();
  });

  // ---- Graph ----

  async function loadGraph() {
    if (state.graphRendered) return;
    var container = $("#graph-container");
    container.innerHTML =
      '<div class="loading-placeholder">Loading graph...</div>';

    try {
      var data = await api("/api/graph");
      var nodes = data.nodes || [];
      var edges = data.edges || [];

      if (!nodes.length) {
        container.innerHTML =
          '<div class="loading-placeholder">No graph data yet. Compile some sources first.</div>';
        return;
      }

      container.innerHTML = "";
      state.graphRendered = true;
      renderGraph(container, nodes, edges);
    } catch (e) {
      container.innerHTML =
        '<div class="loading-placeholder">Failed to load graph: ' +
        e.message +
        "</div>";
    }
  }

  function renderGraph(container, nodes, edges) {
    var width = container.clientWidth;
    var height = container.clientHeight || 600;
    var tooltip = $("#graph-tooltip");

    var conceptColor = "#1e3a5f";
    var sourceColor = "#f59e0b";

    var wordExtent = d3.extent(nodes, function (d) {
      return d.words || 1;
    });
    var sizeScale = d3.scaleSqrt().domain(wordExtent).range([5, 24]);

    var svg = d3
      .select(container)
      .append("svg")
      .attr("width", width)
      .attr("height", height);

    var g = svg.append("g");
    var zoom = d3
      .zoom()
      .scaleExtent([0.2, 5])
      .on("zoom", function (event) {
        g.attr("transform", event.transform);
      });
    svg.call(zoom);

    // Build node id lookup for edges
    var nodeIds = new Set(
      nodes.map(function (n) {
        return n.id;
      }),
    );

    // Filter edges to only those connecting existing nodes
    var validEdges = edges.filter(function (e) {
      return nodeIds.has(e.source) && nodeIds.has(e.target);
    });

    var simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink(validEdges)
          .id(function (d) {
            return d.id;
          })
          .distance(100),
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force(
        "collision",
        d3.forceCollide().radius(function (d) {
          return sizeScale(d.words || 1) + 4;
        }),
      );

    var link = g
      .append("g")
      .selectAll("line")
      .data(validEdges)
      .enter()
      .append("line")
      .attr("stroke", "#d1d5db")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 1);

    var node = g
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .enter()
      .append("circle")
      .attr("r", function (d) {
        return sizeScale(d.words || 1);
      })
      .attr("fill", function (d) {
        return d.group === "concept" ? conceptColor : sourceColor;
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .attr("cursor", "pointer")
      .call(
        d3
          .drag()
          .on("start", function (event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", function (event, d) {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", function (event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }),
      );

    // Labels
    var labels = g
      .append("g")
      .selectAll("text")
      .data(nodes)
      .enter()
      .append("text")
      .text(function (d) {
        return d.id.length > 20 ? d.id.substring(0, 20) + "..." : d.id;
      })
      .attr("font-size", "10px")
      .attr("fill", "#374151")
      .attr("text-anchor", "middle")
      .attr("dy", function (d) {
        return sizeScale(d.words || 1) + 14;
      })
      .style("pointer-events", "none");

    // Hover tooltip
    node
      .on("mouseover", function (event, d) {
        tooltip.classList.remove("hidden");
        tooltip.textContent =
          d.id + " (" + (d.words || 0) + " words, " + d.group + ")";
        tooltip.style.left = event.clientX + 12 + "px";
        tooltip.style.top = event.clientY - 8 + "px";
        d3.select(this).attr("stroke", "#000").attr("stroke-width", 2.5);
      })
      .on("mousemove", function (event) {
        tooltip.style.left = event.clientX + 12 + "px";
        tooltip.style.top = event.clientY - 8 + "px";
      })
      .on("mouseout", function () {
        tooltip.classList.add("hidden");
        d3.select(this).attr("stroke", "#fff").attr("stroke-width", 1.5);
      });

    // Click to navigate to article
    node.on("click", function (event, d) {
      var match = state.articles.find(function (a) {
        return a.title === d.id;
      });
      if (match) {
        switchView("browse");
        setTimeout(function () {
          openArticle(match.path);
        }, 50);
      }
    });

    simulation.on("tick", function () {
      link
        .attr("x1", function (d) {
          return d.source.x;
        })
        .attr("y1", function (d) {
          return d.source.y;
        })
        .attr("x2", function (d) {
          return d.target.x;
        })
        .attr("y2", function (d) {
          return d.target.y;
        });
      node
        .attr("cx", function (d) {
          return d.x;
        })
        .attr("cy", function (d) {
          return d.y;
        });
      labels
        .attr("x", function (d) {
          return d.x;
        })
        .attr("y", function (d) {
          return d.y;
        });
    });
  }

  window.addEventListener("resize", function () {
    if (state.currentView === "graph" && state.graphRendered) {
      state.graphRendered = false;
      loadGraph();
    }
  });

  // ---- Keyboard shortcuts ----
  var viewKeys = {
    1: "dashboard",
    2: "browse",
    3: "search",
    4: "chat",
    5: "graph",
  };
  document.addEventListener("keydown", function (e) {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
    if (viewKeys[e.key]) switchView(viewKeys[e.key]);
  });

  // ---- Init ----
  loadDashboard();
})();
