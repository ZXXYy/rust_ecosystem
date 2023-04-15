#![crate_name = "unsafe_analysis"]
#![crate_type = "dylib"]
#![feature(rustc_private)]

extern crate rustc_driver;
extern crate rustc_hir;
extern crate rustc_lint;
extern crate rustc_interface;
extern crate rustc_middle;
extern crate rustc_span;
extern crate rustc_target;
extern crate rustc_index;
extern crate rustc_const_eval;
#[macro_use] extern crate rustc_lint_defs;

extern crate serde;
extern crate serde_json;

extern crate decls;

// use rustc_driver::plugin::Registry;
use rustc_lint::{LateLintPass, LateContext}; // LateContext
use rustc_hir::hir_id::HirId;
use rustc_middle::ty::TyCtxt;

use decls::functions::FnInfo;
// use crate::blocks::{UnsafeBlocksVisitorData};
mod blocks;
mod items;
mod utils;

// declare the metadata of a particular lint via the declare_lint! macro
// Declare a lint called `HIDDEN_UNSAFE`
declare_lint!(pub HIDDEN_UNSAFE, Allow, "Unsafe analysis");
// This declares a struct and a lint pass, providing a list of associated lints.
// declare_lint_pass!(Functions => [HIDDEN_UNSAFE]);
impl_lint_pass!(Functions => [HIDDEN_UNSAFE]);

pub struct Functions {
    // unsafe_functions: Vec<HirId>,
    // safe_functions: Vec<HirId>,
    all_fn_ids: Vec<HirId>,
    all_fn_infos: Vec<FnInfo>,
    unsafe_fn_num: i32,
    safe_fn_num: i32,
}

impl Functions {

    pub fn new() -> Self {
        Self {
            // unsafe_functions: Vec::new(),
            // safe_functions: Vec::new(),
            all_fn_infos: Vec::new(),
            all_fn_ids: Vec::new(),
            unsafe_fn_num: 0,
            safe_fn_num: 0,
        }
    }

    fn add<'tcx>(&mut self, tcx: TyCtxt<'tcx>, node_id: HirId, unsafety: rustc_hir::Unsafety) {
        let decl_unsafety: bool;
        match unsafety {
            rustc_hir::Unsafety::Normal => {
                decl_unsafety = false;
                self.safe_fn_num += 1;
            }
            rustc_hir::Unsafety::Unsafe => {
                decl_unsafety = true;
                self.unsafe_fn_num += 1;
            }
        }
        let span = tcx.hir().span(node_id);
        let fn_node = tcx.hir().get(node_id);
        if let Some(body_id) = fn_node.body_id(){
            let body_span = tcx.hir().span(body_id.hir_id);
                self.all_fn_infos.push(FnInfo::new(utils::get_node_name(tcx, tcx.hir().local_def_id(node_id).to_def_id()),
                                                tcx.hir().node_to_string(node_id),
                                                utils::get_line(&tcx, span),
                                                utils::get_line(&tcx, body_span),
                                                decl_unsafety));
        }
            
        self.all_fn_ids.push(node_id);
    }
}

impl<'tcx> LateLintPass<'tcx> for Functions {
    fn check_crate(&mut self, _: &LateContext<'tcx>) {
    }
    //========= for function safety analysis ==================
    fn check_body(&mut self, cx: &LateContext<'tcx>, body: &'tcx rustc_hir::Body) {
        //need to find fn/method declaration of this body
        let owner_def_id = cx.tcx.hir().body_owner_def_id(body.id());
        if owner_def_id.to_def_id().is_local() {
            let owner_hir_id = cx.tcx.hir().local_def_id_to_hir_id(owner_def_id);
            let node = cx.tcx.hir().get(owner_hir_id);
            match node {
                rustc_hir::Node::Item(item) => {
                    // functions
                    if let rustc_hir::ItemKind::Fn(ref fn_sig, ref _fn_generic, _) = item.kind {
                        self.add(cx.tcx, owner_hir_id, fn_sig.header.unsafety);
                    }
                },
                rustc_hir::Node::ImplItem(ref impl_item) => {
                    // method implementations
                    if let rustc_hir::ImplItemKind::Fn(ref sig, _) = impl_item.kind {
                        self.add(cx.tcx, owner_hir_id, sig.header.unsafety);
                    }
                }
                rustc_hir::Node::Expr(ref _expr) => {}//closure nothing to do
                rustc_hir::Node::AnonConst(ref _anon_const) => {
                    // nothing to do - this is not a stand alone function
                    // any unsafe in this body will be processed by the enclosing function or method
                }
                rustc_hir::Node::TraitItem(ref trait_item) => {
                    // associated methods (functions in impl blocks, not of traits)
                    match trait_item.kind {
                        rustc_hir::TraitItemKind::Const(..)
                        | rustc_hir::TraitItemKind::Type(..) => { }
                        rustc_hir::TraitItemKind::Fn(ref sig, ref _trait_method) => {
                            if trait_item.defaultness.has_value(){
                                self.add(cx.tcx, owner_hir_id, sig.header.unsafety);
                            }
                        }
                    }
                }
                _ => {
                    panic!("Not handled {:?} ", node);
                }
            }
        }
    }

    fn check_crate_post(&mut self, cx: &LateContext<'tcx>) {
        let root_dir = utils::get_root_dir();
        let cnv = utils::local_crate_name_and_version();
        let file_ops = decls::FileOps::new(&cnv.0, &cnv.2,&cnv.3, &root_dir);

        // get function infos
        let mut fn_file = file_ops.create_file (decls::FUNCTIONS);
        utils::save_meta_info(self.safe_fn_num, self.unsafe_fn_num, &mut fn_file);
        utils::save_analysis(self.all_fn_infos.clone(), &mut fn_file);

        // unsafe block, function, traits and traits impl analysis
        let mut impls_file = file_ops.create_file (decls::UNSAFE_TRAITS_IMPLS);
        let mut traits_file = file_ops.create_file (decls::UNSAFE_TRAITS);
        
        let result = items::run_analysis(cx);
        utils::save_analysis(result.unsafe_traits_impls, &mut impls_file);
        utils::save_analysis(result.unsafe_traits, &mut traits_file);

        // get block infos
        let (unsafe_cnt, safe_cnt, block_infos) = blocks::run_sources_analysis(cx, &self.all_fn_ids);
        let mut file = file_ops.create_file (decls::BLOCKS_IN_FUNCTIONS);
        utils::save_meta_info(safe_cnt, unsafe_cnt, &mut file);
        utils::save_analysis(block_infos, &mut file);
        
    }
}