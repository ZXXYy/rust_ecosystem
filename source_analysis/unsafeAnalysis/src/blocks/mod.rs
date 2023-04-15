use rustc_lint::LateContext;
use rustc_middle::ty::TyCtxt;
use rustc_middle::hir::map::Map;
use rustc_hir::def_id::DefId;
use rustc_hir::hir_id::HirId;

use decls::blocks::BlockUnsafety;
use crate::utils::{get_line};

pub fn run_sources_analysis<'a, 'tcx>(cx: &LateContext<'tcx>
                                      , fns: &Vec<HirId>)
                                      -> (i32, i32, Vec<Vec<BlockUnsafety>>) {
    let mut result = Vec::new();
    let mut unsafe_cnt:i32 = 0;
    let mut safe_cnt:i32 = 0;
    // get blocks inside functions
    for &fn_id in fns {
        let fn_def_id = cx.tcx.hir().local_def_id(fn_id).to_def_id();
        if let Some(tup) = get_blocks(cx.tcx, fn_id, fn_def_id){
            if tup.2.len() > 0{
                result.push(tup.2);
                unsafe_cnt += tup.0;
                safe_cnt += tup.1;
            }
            // println!("Fn name: {}", get_fn_path(&cx.tcx, fn_def_id));  
            // println!("Fn span: {} {}", get_line(&cx.tcx, span), blocks[0].block_span);  
        }
    }
    (unsafe_cnt, safe_cnt, result)
}

fn get_blocks<'a, 'tcx>(tcx: TyCtxt<'tcx>, fn_hir_id: HirId, fn_id: DefId) -> Option<(i32, i32, Vec<BlockUnsafety>) > {
    let mut body_visitor =  UnsafeBlocksVisitorData {
        tcx: tcx,
        fn_hir_id: fn_hir_id,
        blocks: Vec::new(),
        unsafe_block_cnt: 0,
        safe_block_cnt: 0
    };
    if let Some(fn_node) = tcx.hir().get_if_local(fn_id) {
        // Given a HirId, returns the BodyId associated with it, if the node is a body owner, otherwise returns None.
        let body_id_opt = fn_node.body_id();
        match body_id_opt {
            Some(body_id) => {
                let body = tcx.hir().body(body_id);
                rustc_hir::intravisit::walk_body(&mut body_visitor, body);
                Some((body_visitor.unsafe_block_cnt, body_visitor.safe_block_cnt,body_visitor.blocks))
            }
            None => None
        }
    } else {
        None
    }
}

////////////////////////////////////////////////////////////////////
pub struct UnsafeBlocksVisitorData<'tcx> {
    pub tcx: TyCtxt<'tcx>,
    pub fn_hir_id: HirId,
    pub blocks: Vec<BlockUnsafety>,
    pub unsafe_block_cnt: i32,
    pub safe_block_cnt: i32
}

impl<'tcx> UnsafeBlocksVisitorData<'tcx>{
    pub fn add_block(&mut self, b: &'tcx rustc_hir::Block,  unsafety: bool){
        // println!("Block span: {}", get_line(&self.tcx, b.span));  
        // println!("Block safety: {}", unsafety); 
        self.blocks.push(BlockUnsafety::new(self.tcx.hir().node_to_string(self.fn_hir_id),
                                            get_line(&self.tcx, b.span), 
                                            unsafety));
    }
}

impl<'tcx> rustc_hir::intravisit::Visitor<'tcx> for UnsafeBlocksVisitorData<'tcx> {
    type Map = Map<'tcx>;
    type NestedFilter = rustc_middle::hir::nested_filter::All;
    fn nested_visit_map<'this>(&'this mut self) -> Self::Map {
        self.tcx.hir()
    }

    fn visit_block(&mut self, b: &'tcx rustc_hir::Block) {
        match b.rules {
            rustc_hir::BlockCheckMode::DefaultBlock => {
                // self.add_block(b, false);
                self.safe_block_cnt += 1;
            }
            rustc_hir::BlockCheckMode::UnsafeBlock(unsafe_source) => {
                match unsafe_source {
                    rustc_hir::UnsafeSource::UserProvided => {
                       self.add_block(b, true);
                       self.unsafe_block_cnt += 1;
                    }
                    rustc_hir::UnsafeSource::CompilerGenerated => {
                    }
                }
            }
        }
        rustc_hir::intravisit::walk_block(self, b);
    }

}