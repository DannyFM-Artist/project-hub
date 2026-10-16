import sys
from project_hub.hub import Hub
h=Hub(sys.argv[1])
def mk(id,name,desc,status,phases,nxt):
    h.create_project(id,name,desc,phases=phases)
    h.update_project(id,status=status,next_step=nxt)
mk("framegrade","framegrade","GPU video transcoder, ACES pipeline","active",["Ingest pipeline","Colour pipeline","GPU decode","Batch queue","Export presets","Packaging"],"Profile the NVDEC path on 10-bit ProRes 4444")
mk("cuedeck","cuedeck","Companion + OSC show control","active",["Core","OSC","LED processor presets","Docs","Release"],"Map Brompton presets to OSC macro buttons")
mk("project-hub","project-hub","this dashboard + MCP server","active",["Data layer + tests","MCP","Dashboard","CLI"],"Concurrent-write test with two processes")
mk("moyad-studio","moyad.studio","portfolio site + reel","paused",["Design","Build","Content","Reel page","Launch"],"Waiting on a 30 s reel export")
mk("led-mapper","led-mapper","LED wall pixel-map generator","done",["Release"],"")
mk("stagetimer","stagetimer-ios","iPhone show countdown clock","parked",["A","B","Timecode sync"],"Revisit once cuedeck exposes LTC")
p=h.get_project("framegrade")
for i,(ph,st) in enumerate(zip(p["phases"],["done","done","in_progress"])): h.set_phase_status("framegrade",ph["id"],st,"NVDEC works for HEVC" if i==2 else None)
for t,ti,st in [("bug","Banding on 8-bit export","open"),("idea","Scopes panel","open"),("future_request","Watch-folder mode","open"),("idea","Per-clip LUT","planned"),("bug","Crash on GPU OOM","done"),("bug","Old thing","discarded")]:
    it=h.add_item("framegrade",t,ti,"some details");
    if st!="open": h.update_item("framegrade",it["id"],status=st)
h.log_decision("framegrade","Decode with NVDEC, fall back to FFmpeg","4x faster on 4K HEVC")
h.log_decision("framegrade","ACES 1.3 working space","matches Resolve <b>x</b>")
h.post_message("framegrade","report","Session report: GPU decode","+ NVDEC at 212 fps\n- ProRes still software\n→ next: profile","framegrade")
h.post_message("framegrade","task","Export a 30 s reel","H.264 1080p","moyad-studio")
h.post_message("all","message","Hello all <script>alert(1)</script>","body","cuedeck")
h.post_message("cuedeck","message","Hi cuedeck","x")
