"""
TRS Streamlit UI with Proposal Workflow

Pages:
- Dashboard: Overview and stats
- Registry Browser: Browse all tags
- Tag Inspector: View tag details
- Search: Resolve terms to tags
- ---
- Propose Tag: Submit new proposals
- Review Queue: Review pending proposals
- ---
- Releases: Release dashboard
- Contracts: View contracts
- Audit Log: View all actions
"""

import os
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

API_URL = os.getenv("TRS_API_URL", "http://localhost:8401")

st.set_page_config(
    page_title="Tag Registry Service",
    page_icon="🏷️",
    layout="wide",
)

# Session state for API key
if "api_key" not in st.session_state:
    st.session_state.api_key = ""


def get_headers():
    """Get headers with API key if set."""
    headers = {}
    if st.session_state.api_key:
        headers["X-API-Key"] = st.session_state.api_key
    return headers


def get_json(path, params=None):
    """GET request to API."""
    try:
        r = requests.get(f"{API_URL}{path}", params=params, headers=get_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None


def post_json(path, data):
    """POST request to API."""
    try:
        r = requests.post(f"{API_URL}{path}", json=data, headers=get_headers(), timeout=30)
        if r.status_code == 401:
            st.error("Authentication required. Enter your API key in the sidebar.")
            return None
        if r.status_code == 403:
            st.error("Permission denied. You don't have the required role.")
            return None
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {e}")
        return None


# Sidebar
st.sidebar.title("🏷️ Tag Registry")

# API Key input
with st.sidebar.expander("🔑 Authentication", expanded=not st.session_state.api_key):
    api_key = st.text_input(
        "API Key",
        value=st.session_state.api_key,
        type="password",
        help="Enter your TRS API key for write access",
    )
    if api_key != st.session_state.api_key:
        st.session_state.api_key = api_key
        st.rerun()
    
    if st.session_state.api_key:
        st.success("🔓 Authenticated")
    else:
        st.info("Read-only mode. Enter API key for write access.")

st.sidebar.divider()

# Navigation
page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard",
        "📚 Registry Browser",
        "🔍 Tag Inspector",
        "🔎 Search",
        "📈 Registry Stats",
        "---",
        "➕ Propose Tag",
        "📝 Review Queue",
        "---",
        "🚀 Releases",
        "📄 Contracts",
        "📋 Audit Log",
        "⚡ System Metrics",
    ],
)

# Handle dividers
if page.startswith("---"):
    page = "📊 Dashboard"

# ============================================================================
# Dashboard
# ============================================================================
if page == "📊 Dashboard":
    st.title("📊 Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Registry Status")
        status = get_json("/status")
        if status:
            st.metric("Tags", status.get("counts", {}).get("tag_count", 0))
            st.metric("Version", status.get("core_version", "unknown"))
            st.metric("Contracts", status.get("counts", {}).get("contracts_files", 0))
    
    with col2:
        st.subheader("Proposal Queue")
        stats = get_json("/api/proposals/stats")
        if stats:
            col2a, col2b, col2c = st.columns(3)
            col2a.metric("Pending", stats.get("pending", 0))
            col2b.metric("Approved", stats.get("approved", 0))
            col2c.metric("Total", stats.get("total", 0))
    
    st.divider()
    
    # Recent proposals
    st.subheader("Recent Proposals")
    proposals = get_json("/api/proposals", params={"limit": 10})
    if proposals:
        for p in proposals[:5]:
            status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌", "merged": "🔄"}.get(p["status"], "❓")
            st.write(f"{status_emoji} **{p['tag_id']}** — {p['proposal_type']} by {p['submitter']} ({p['status']})")
    else:
        st.info("No proposals yet.")

# ============================================================================
# Registry Browser
# ============================================================================
elif page == "📚 Registry Browser":
    st.title("📚 Registry Browser")
    
    reg = get_json("/registry")
    if not reg:
        st.stop()
    
    tags = reg.get("tags", {})
    rows = []
    
    if isinstance(tags, dict):
        for k, v in tags.items():
            if isinstance(v, dict):
                rows.append({
                    "tag_id": k,
                    "canonical_name": v.get("canonical_name") or v.get("name"),
                    "status": v.get("status"),
                    "value_type": v.get("value_type"),
                    "domain": v.get("domain"),
                    "subdomain": v.get("subdomain"),
                })
    
    df = pd.DataFrame(rows)
    if df.empty:
        st.warning("No tags found.")
        st.stop()
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        domains = ["(all)"] + sorted([d for d in df["domain"].dropna().unique() if str(d).strip()])
        domain = st.selectbox("Domain", domains)
    
    with col2:
        statuses = ["(all)"] + sorted([s for s in df["status"].dropna().unique() if str(s).strip()])
        status = st.selectbox("Status", statuses)
    
    with col3:
        search = st.text_input("Filter by name/ID")
    
    # Apply filters
    if domain != "(all)":
        df = df[df["domain"] == domain]
    if status != "(all)":
        df = df[df["status"] == status]
    if search:
        mask = df["tag_id"].str.contains(search, case=False, na=False) | \
               df["canonical_name"].str.contains(search, case=False, na=False)
        df = df[mask]
    
    st.write(f"Showing {len(df)} of {len(rows)} tags")
    st.dataframe(df, use_container_width=True, height=500)

# ============================================================================
# Tag Inspector
# ============================================================================
elif page == "🔍 Tag Inspector":
    st.title("🔍 Tag Inspector")
    
    reg = get_json("/registry")
    if not reg:
        st.stop()
    
    tags = reg.get("tags", {})
    if not isinstance(tags, dict) or not tags:
        st.warning("No tags found.")
        st.stop()
    
    tag_id = st.selectbox("Select Tag", sorted(tags.keys()))
    
    if tag_id:
        tag = tags[tag_id]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Info")
            st.write(f"**Canonical Name:** {tag.get('canonical_name')}")
            st.write(f"**Status:** {tag.get('status')}")
            st.write(f"**Value Type:** {tag.get('value_type')}")
            st.write(f"**Domain:** {tag.get('domain')}")
            st.write(f"**Definition:** {tag.get('definition', 'N/A')}")
        
        with col2:
            st.subheader("Extractability")
            extract = tag.get("extractability", {})
            st.write(f"**From 2D:** {extract.get('from_2d', 'N/A')}")
            st.write(f"**From 3D/VR:** {extract.get('from_3d_vr', 'N/A')}")
            st.write(f"**Monocular 3D:** {extract.get('monocular_3d_approx', 'N/A')}")
        
        with st.expander("Full JSON"):
            st.json(tag)

# ============================================================================
# Search
# ============================================================================
elif page == "🔎 Search":
    st.title("🔎 Search Tags")
    
    term = st.text_input("Search term (alias, name, or tag ID)", "")
    
    if term.strip():
        results = get_json("/resolve", params={"term": term, "limit": 25})
        if results:
            matches = results.get("matches", [])
            st.write(f"Found {len(matches)} matches for '{term}'")
            
            for m in matches:
                with st.expander(f"**{m['tag_id']}** — {m.get('canonical_name', '')}"):
                    st.write(f"Status: {m.get('status')}")
                    st.write(f"Value Type: {m.get('value_type')}")
                    st.write(f"Domain: {m.get('domain')}")

# ============================================================================
# Registry Stats
# ============================================================================
elif page == "📈 Registry Stats":
    st.title("📈 Registry Statistics")
    
    stats = get_json("/api/stats")
    
    if stats:
        st.metric("Total Tags", stats.get("total_tags", 0))
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("By Status")
            for status, count in sorted(stats.get("by_status", {}).items()):
                st.write(f"**{status}**: {count}")
        
        with col2:
            st.subheader("By Value Type")
            for vtype, count in sorted(stats.get("by_value_type", {}).items()):
                st.write(f"**{vtype}**: {count}")
        
        with col3:
            st.subheader("By Domain")
            for domain, count in sorted(stats.get("by_domain", {}).items(), key=lambda x: -x[1]):
                domain_short = domain[:30] + "..." if len(domain) > 30 else domain
                st.write(f"**{domain_short}**: {count}")
        
        st.divider()
        
        # Fuzzy search
        st.subheader("🔍 Smart Search")
        search_query = st.text_input("Search (fuzzy matching)", placeholder="e.g., 'warm light' or 'ceiling'")
        
        col1, col2 = st.columns(2)
        with col1:
            domains = get_json("/api/domains")
            domain_filter = st.selectbox("Filter by Domain", ["(all)"] + (domains.get("domains", []) if domains else []))
        with col2:
            status_filter = st.selectbox("Filter by Status", ["(all)", "active", "deprecated", "experimental"])
        
        if search_query:
            params = {"q": search_query, "limit": 25}
            if domain_filter != "(all)":
                params["domain"] = domain_filter
            if status_filter != "(all)":
                params["status"] = status_filter
            
            search_results = get_json("/api/search", params=params)
            
            if search_results:
                st.write(f"Found {search_results.get('count', 0)} results")
                
                for r in search_results.get("results", []):
                    score = r.get("score", 0)
                    score_color = "🟢" if score > 0.8 else "🟡" if score > 0.6 else "🔴"
                    
                    with st.expander(f"{score_color} **{r['tag_id']}** ({score:.0%})"):
                        st.write(f"**Name:** {r.get('canonical_name', 'N/A')}")
                        st.write(f"**Definition:** {r.get('definition', 'N/A')}")
                        st.write(f"**Status:** {r.get('status')} | **Type:** {r.get('value_type')}")
                        if r.get("match_field"):
                            st.caption(f"Matched: {r['match_field']}")

# ============================================================================
# Propose Tag
# ============================================================================
elif page == "➕ Propose Tag":
    st.title("➕ Propose New Tag")
    
    if not st.session_state.api_key:
        st.warning("⚠️ Authentication required to submit proposals. Enter your API key in the sidebar.")
        st.stop()
    
    with st.form("proposal_form"):
        st.subheader("Tag Details")
        
        proposal_type = st.selectbox(
            "Proposal Type",
            ["new_tag", "modify_tag", "deprecate_tag"],
            help="new_tag: Add a new tag, modify_tag: Change existing tag, deprecate_tag: Mark tag as deprecated"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            canonical_name = st.text_input("Canonical Name*", help="Human-readable name")
            tag_id = st.text_input(
                "Tag ID*",
                help="Format: category.domain.attribute (e.g., env.lighting.warmth)"
            )
        
        with col2:
            domain = st.selectbox("Domain", [
                "A. Luminous Environment",
                "B. Chromatic Environment",
                "C. Material and Texture",
                "D. Geometric Pattern and Form",
                "E. Spatial Configuration",
                "F. Order and Maintenance",
                "G. Nature and Biophilia",
                "H. Furnishing and Function",
                "I. Social and Cultural",
                "J. Safety and Security",
                "K. Acoustic Environment",
                "L. Thermal Environment",
                "M. Olfactory Environment",
                "N. Signs and Symbols",
            ])
            value_type = st.selectbox("Value Type", ["ordinal", "binary", "continuous", "categorical"])
        
        definition = st.text_area("Definition*", help="Clear description of what this tag measures")
        
        st.subheader("Evidence")
        evidence_doi = st.text_input("Evidence DOI", placeholder="https://doi.org/10.xxxx/...")
        reason = st.text_area("Reason for Proposal", help="Why is this tag needed?")
        
        st.subheader("Aliases")
        aliases_text = st.text_input("Aliases (comma-separated)", help="Alternative names for this tag")
        
        submitted = st.form_submit_button("Submit Proposal", type="primary")
        
        if submitted:
            if not all([canonical_name, tag_id, definition]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                # Build payload
                payload = {
                    "canonical_name": canonical_name,
                    "category": "environmental",
                    "value_type": value_type,
                    "status": "proposed",
                    "domain": domain,
                    "definition": definition,
                    "semantics": {
                        "aliases": [a.strip() for a in aliases_text.split(",") if a.strip()]
                    }
                }
                
                result = post_json("/api/proposals", {
                    "proposal_type": proposal_type,
                    "tag_id": tag_id,
                    "canonical_name": canonical_name,
                    "payload": payload,
                    "evidence_doi": evidence_doi or None,
                    "reason": reason or None,
                })
                
                if result:
                    st.success(f"✅ Proposal #{result['id']} submitted successfully!")
                    st.balloons()

# ============================================================================
# Review Queue
# ============================================================================
elif page == "📝 Review Queue":
    st.title("📝 Review Queue")
    
    # Status filter
    status_filter = st.selectbox("Filter by Status", ["pending", "approved", "rejected", "all"])
    
    params = {"limit": 50}
    if status_filter != "all":
        params["status"] = status_filter
    
    proposals = get_json("/api/proposals", params=params)
    
    if not proposals:
        st.info("No proposals found.")
        st.stop()
    
    st.write(f"Showing {len(proposals)} proposals")
    
    for p in proposals:
        status_emoji = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌",
            "merged": "🔄",
            "withdrawn": "🚫",
        }.get(p["status"], "❓")
        
        with st.expander(f"{status_emoji} **{p['tag_id']}** — {p['canonical_name'] or p['proposal_type']}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Type:** {p['proposal_type']}")
                st.write(f"**Submitter:** {p['submitter']}")
                st.write(f"**Submitted:** {p['created_at']}")
                if p.get("reason"):
                    st.write(f"**Reason:** {p['reason']}")
                if p.get("evidence_doi"):
                    st.write(f"**Evidence:** {p['evidence_doi']}")
            
            with col2:
                st.write(f"**Status:** {p['status']}")
                st.write(f"**ID:** #{p['id']}")
            
            with st.expander("View Payload"):
                st.json(p.get("payload", {}))
            
            # Review actions (only for pending)
            if p["status"] == "pending" and st.session_state.api_key:
                st.divider()
                st.write("**Review Actions**")
                
                comment = st.text_input(f"Comment for #{p['id']}", key=f"comment_{p['id']}")
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("✅ Approve", key=f"approve_{p['id']}", type="primary"):
                        result = post_json(f"/api/proposals/{p['id']}/review", {
                            "decision": "approve",
                            "comment": comment or None,
                        })
                        if result:
                            st.success("Approved!")
                            st.rerun()
                
                with col_b:
                    if st.button("❌ Reject", key=f"reject_{p['id']}"):
                        result = post_json(f"/api/proposals/{p['id']}/review", {
                            "decision": "reject",
                            "comment": comment or "Rejected",
                        })
                        if result:
                            st.warning("Rejected.")
                            st.rerun()
                
                with col_c:
                    if st.button("📝 Request Changes", key=f"changes_{p['id']}"):
                        if not comment:
                            st.error("Please provide a comment explaining requested changes.")
                        else:
                            result = post_json(f"/api/proposals/{p['id']}/review", {
                                "decision": "request_changes",
                                "comment": comment,
                            })
                            if result:
                                st.info("Changes requested.")
                                st.rerun()

# ============================================================================
# Releases
# ============================================================================
elif page == "🚀 Releases":
    st.title("🚀 Release Dashboard")
    
    # Stats
    col1, col2, col3 = st.columns(3)
    
    stats = get_json("/api/proposals/stats")
    status = get_json("/status")
    latest = get_json("/api/releases/latest")
    
    with col1:
        st.metric("Current Version", status.get("core_version", "unknown") if status else "?")
    
    with col2:
        st.metric("Pending Proposals", stats.get("pending", 0) if stats else 0)
    
    with col3:
        st.metric("Approved (Ready)", stats.get("approved", 0) if stats else 0)
    
    st.divider()
    
    # Release form
    if st.session_state.api_key:
        with st.expander("🚀 Create New Release"):
            with st.form("release_form"):
                version = st.text_input("Version", placeholder="v0.2.9")
                release_notes = st.text_area("Release Notes")
                
                if st.form_submit_button("Create Release", type="primary"):
                    if not version or not version.startswith("v"):
                        st.error("Version must start with 'v' (e.g., v0.2.9)")
                    else:
                        result = post_json("/api/releases", {
                            "version": version,
                            "release_notes": release_notes or None,
                        })
                        if result:
                            st.success(f"Release {version} created!")
                            st.rerun()
    
    st.divider()
    
    # Release history
    st.subheader("Release History")
    releases = get_json("/api/releases", params={"limit": 20})
    
    if releases:
        for r in releases:
            with st.expander(f"**{r['version']}** — {r['created_at'][:10]}"):
                st.write(f"**Released by:** {r['released_by']}")
                st.write(f"**Previous:** {r.get('previous_version') or 'N/A'}")
                st.write(f"**Changes:** +{r['tags_added']} / ~{r['tags_modified']} / -{r['tags_removed']}")
                if r.get("release_notes"):
                    st.write(f"**Notes:** {r['release_notes']}")
    else:
        st.info("No releases recorded yet.")

# ============================================================================
# Contracts
# ============================================================================
elif page == "📄 Contracts":
    st.title("📄 Contracts")
    
    consumer = st.selectbox(
        "Consumer",
        ["image_tagger", "article_eater", "bn", "preference_testing"],
    )
    
    contract = get_json("/contracts/latest", params={"consumer": consumer})
    
    if contract:
        meta = contract.get("meta", {})
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Version", meta.get("contract_version", "?"))
        col2.metric("Tags", len(contract.get("tags", [])))
        col3.metric("SHA256", meta.get("registry_sha256", "?")[:12] + "...")
        
        with st.expander("View Full Contract"):
            st.json(contract)

# ============================================================================
# Audit Log
# ============================================================================
elif page == "📋 Audit Log":
    st.title("📋 Audit Log")
    
    if not st.session_state.api_key:
        st.warning("⚠️ Authentication required to view audit log.")
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        action_filter = st.selectbox("Filter by Action", ["(all)", "proposal_created", "proposal_reviewed", "release_created", "api_access"])
    
    with col2:
        limit = st.number_input("Limit", min_value=10, max_value=500, value=100)
    
    params = {"limit": limit}
    if action_filter != "(all)":
        params["action"] = action_filter
    
    entries = get_json("/api/audit", params=params)
    
    if entries:
        for e in entries:
            timestamp = e.get("timestamp", "")[:19]
            action = e.get("action", "")
            user = e.get("user_id", "")
            target = f"{e.get('target_type', '')}/{e.get('target_id', '')}" if e.get("target_type") else ""
            
            st.write(f"`{timestamp}` | **{action}** | {user} | {target}")
    else:
        st.info("No audit entries found.")

# ============================================================================
# System Metrics
# ============================================================================
elif page == "⚡ System Metrics":
    st.title("⚡ System Metrics")
    
    # Health status
    st.subheader("🏥 System Health")
    health = get_json("/dashboard/health")
    
    if health:
        status = "🟢 Healthy" if health.get("healthy") else "🔴 Unhealthy"
        st.markdown(f"**Status:** {status}")
        
        deps = health.get("dependencies", [])
        
        cols = st.columns(len(deps))
        for i, dep in enumerate(deps):
            with cols[i]:
                name = dep.get("name", "Unknown")
                is_healthy = dep.get("healthy", False)
                icon = "✅" if is_healthy else "❌"
                st.metric(name.capitalize(), icon)
                
                if "latency_ms" in dep:
                    st.caption(f"{dep['latency_ms']:.1f}ms")
                
                if "error" in dep:
                    st.error(dep["error"])
    
    st.divider()
    
    # Metrics
    st.subheader("📊 Performance Metrics")
    metrics_data = get_json("/dashboard/metrics")
    
    if metrics_data:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            uptime = metrics_data.get("uptime_seconds", 0)
            hours = int(uptime // 3600)
            mins = int((uptime % 3600) // 60)
            st.metric("Uptime", f"{hours}h {mins}m")
        
        with col2:
            active = metrics_data.get("requests", {}).get("active", 0)
            st.metric("Active Requests", active)
        
        with col3:
            cache = metrics_data.get("cache", {})
            hit_rate = cache.get("hit_rate", 0)
            st.metric("Cache Hit Rate", f"{hit_rate:.0%}")
        
        with col4:
            db = metrics_data.get("database", {})
            queries = db.get("query_count", 0)
            st.metric("DB Queries", queries)
        
        # Business metrics
        st.subheader("📈 Business Metrics")
        biz = metrics_data.get("business", {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Proposals Created", biz.get("proposals_created", 0))
        with col2:
            st.metric("Proposals Approved", biz.get("proposals_approved", 0))
        with col3:
            st.metric("Releases", biz.get("releases_created", 0))
        with col4:
            st.metric("Searches", biz.get("searches_performed", 0))
        
        # Errors
        errors = metrics_data.get("errors", {})
        if errors:
            st.subheader("⚠️ Errors")
            for error_type, count in errors.items():
                st.write(f"**{error_type}**: {count}")
    
    st.divider()
    
    # Database stats
    st.subheader("🗄️ Database")
    db_stats = get_json("/dashboard/database")
    
    if db_stats and "tables" in db_stats:
        col1, col2 = st.columns(2)
        
        with col1:
            size_mb = db_stats.get("size_bytes", 0) / (1024 * 1024)
            st.metric("Database Size", f"{size_mb:.2f} MB")
        
        with col2:
            tables = db_stats.get("tables", {})
            total_rows = sum(tables.values())
            st.metric("Total Rows", total_rows)
        
        with st.expander("Table Details"):
            for table, count in sorted(tables.items()):
                st.write(f"**{table}**: {count:,} rows")
    
    # System info
    st.divider()
    st.subheader("💻 System Info")
    sys_info = get_json("/dashboard/system")
    
    if sys_info:
        st.json(sys_info)
