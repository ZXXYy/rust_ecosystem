use std::env;
use std::io::Write;
use std::fs::File;
use std::fmt::Write as FmtWrite;

use rustc_middle::ty::TyCtxt;
use rustc_hir::def_id::DefId;

pub fn get_root_dir() -> String {
    match env::var("FULL_ANALYSIS_DIR") {
       Ok (val) => {val.to_string()}
       Err (_) => {"./compiler_result".to_string()}
    }
}

pub fn local_crate_name_and_version() -> (String, String, String, String) {
    let pkg = env::var("CARGO_PKG_NAME").unwrap();
    let version = env::var("CARGO_PKG_VERSION").unwrap();
    let cve_id = match env::var("CVE_ID") {
        Ok (val) => {val.to_string()}
        Err (_) => {"".to_string()}
    };
    let hash = match env::var("HASH") {
        Ok (val) => {val.to_string()}
        Err (_) => {"".to_string()}
    };
    (pkg,version,cve_id,hash)
}

pub fn get_node_name<'a, 'tcx>(tcx: TyCtxt<'tcx>, def_id: DefId) -> String {
    tcx.def_path_str(def_id)
}

// ==========useful function==================================
// ====get the file name and line according to SourceInfo.Span
// ==========useful function==================================

// pub fn get_file<'a, 'tcx>(tcx: &TyCtxt<'tcx>, span: rustc_span::Span) -> String {
//     let mut result = String::new();
//     // Looks up source information about a BytePos.
//     let loc = tcx.sess.source_map().lookup_char_pos(span.lo());
//     // let span_string = tcx.sess.source_map().span_to_diagnostic_string(span);
//     let filename = &loc.file.name;
//     if let Err(e) = write!(result, "{:?}", filename){
//         println!("Writing error: {}", e.to_string());  
//     }
//     result
// }

pub fn get_line<'a, 'tcx>(tcx: &TyCtxt<'tcx>, span: rustc_span::Span) -> String {
    let span_string = tcx.sess.source_map().span_to_embeddable_string(span);
    span_string
}

pub fn get_file_and_line<'a, 'tcx>(tcx: &TyCtxt<'tcx>, span: rustc_span::Span) -> String {
    let mut result = String::new();
    // Looks up source information about a BytePos.
    let loc = tcx.sess.source_map().lookup_char_pos(span.lo());
    let span_string = tcx.sess.source_map().span_to_embeddable_string(span);
    let filename = &loc.file.name;
    if let Err(e) = write!(result, "file: {:?} line {:?}", filename, span_string){
        println!("Writing error: {}", e.to_string());  
    }
    result
}

// pub fn get_fn_path<'a, 'tcx>(tcx: &TyCtxt<'tcx>, def_id:DefId) -> String {
//     let mut out = String::new();
//     if let Err(e) = write!(&mut out,"{:?}", tcx.def_path_debug_str(def_id)){
//         println!("Writing error: {}", e.to_string());   
//     }
//     out
// }


// pub fn save_summary_analysis<T>(analysis_results: T, file: &mut File)
//     where
//         T: serde::ser::Serialize,
// {
//     let serialized = serde_json::to_string(&analysis_results).unwrap();
//     writeln!(file, "{}", serialized);
//     file.sync_all();
// }
#[allow(unused_must_use)]
pub fn save_meta_info(safe_cnt: i32, unsafe_cnt: i32, file: &mut File)
{
    writeln!(file, "# of safe function/block: {}", safe_cnt);
    writeln!(file, "# of unsafe function/block: {}", unsafe_cnt);
}
#[allow(unused_must_use)]
pub fn save_analysis<T>(analysis_results: Vec<T>, file: &mut File)
    where
        T: serde::ser::Serialize,
{
    for res in analysis_results {
        let serialized = serde_json::to_string_pretty(&res).unwrap();
        if let Err(e) = writeln!(file, "{}", serialized){
            println!("Writing error: {}", e.to_string());   
        }
    }
    if let Err(e) = file.flush(){
        println!("Flushing error: {}", e.to_string());
    }
    if let Err(e) = file.sync_all(){
        println!("Sync error: {}", e.to_string())
    }
    
}