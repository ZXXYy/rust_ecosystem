use rustc_lint::LateContext;
use rustc_hir::intravisit::{Visitor, FnKind};
use rustc_hir::{FnDecl, BodyId, HirId};
use rustc_hir::def_id::DefId;
use rustc_middle::ty::TyCtxt;
use rustc_middle::hir::map::Map;
use rustc_span::Span;

use decls::items::UnsafeItemInfo;
use crate::utils::{get_node_name, get_file_and_line};
use crate::items::UnsafeItem::{MyUnsafeTraitImpl, MyUnsafeTrait, MyUnsafeBlock, MyUnsafeFn};

pub enum UnsafeItem{
    MyUnsafeTraitImpl,
    MyUnsafeTrait,
    MyUnsafeBlock,
    MyUnsafeFn,
}

pub fn run_analysis(cx: & LateContext<'_>) -> ItemsAnalysis {
    let mut visitor = ItemVisitor::new(cx.tcx);
    cx.tcx.hir().walk_toplevel_module(&mut visitor);
    let mut unsafe_fn: Vec<UnsafeItemInfo> = Vec::new();
    for item in visitor.unsafe_fn {
        let node_name: String = get_node_name(cx.tcx, item.id);
        let file_and_line: String = get_file_and_line(&cx.tcx, item.span);
        unsafe_fn.push(UnsafeItemInfo::new(node_name, false, file_and_line));
    }
    for item in visitor.safe_fn {
        let node_name: String = get_node_name(cx.tcx, item.id);
        let file_and_line: String = get_file_and_line(&cx.tcx, item.span);
        unsafe_fn.push(UnsafeItemInfo::new(node_name, true, file_and_line));
    }
    ItemsAnalysis{
        unsafe_traits_impls: visitor.unsafe_traits_impls,
        unsafe_traits: visitor.unsafe_traits,
        unsafe_fn: unsafe_fn,
    }
}

pub struct ItemsAnalysis {
    pub unsafe_traits_impls: Vec<UnsafeItemInfo>,
    pub unsafe_traits: Vec<UnsafeItemInfo>,
    pub unsafe_fn: Vec<UnsafeItemInfo>,
}

struct ItemCompilerInfo{
    id: DefId,
    span: Span,
}
impl ItemCompilerInfo {
    pub fn new(id: DefId, span: Span) -> Self {
        ItemCompilerInfo { id, span }
    }
}

struct ItemVisitor<'tcx> {
    tcx: TyCtxt<'tcx>,
    unsafe_traits_impls: Vec<UnsafeItemInfo>,
    unsafe_traits: Vec<UnsafeItemInfo>,
    unsafe_fn: Vec<ItemCompilerInfo>,
    safe_fn: Vec<ItemCompilerInfo>,
    unsafe_block_num: i32,
    safe_block_num: i32, 
}

impl<'tcx> ItemVisitor<'tcx> {
    pub fn new(tcx: TyCtxt<'tcx>) -> Self {
        ItemVisitor {
            unsafe_traits_impls: Vec::new(),
            unsafe_traits: Vec::new(),
            safe_fn: Vec::new(),
            unsafe_fn: Vec::new(),
            unsafe_block_num: 0,
            safe_block_num: 0,
            tcx:tcx,
        }
    }

    pub fn add(&mut self, unsafe_item: UnsafeItem, id: DefId, span: Span, safety: bool){
        let node_name: String = get_node_name(self.tcx, id);
        let file_and_line: String = get_file_and_line(&self.tcx, span);
        match unsafe_item{
            MyUnsafeTraitImpl => {
                self.unsafe_traits_impls.push(UnsafeItemInfo::new(node_name, safety, file_and_line));
            }
            MyUnsafeTrait => {
                self.unsafe_traits.push(UnsafeItemInfo::new(node_name, safety, file_and_line));
            }
            MyUnsafeBlock => {
                if let Some(index) = self.safe_fn.iter().position(|info| (*info).id == id){
                    self.safe_fn.remove(index);
                }
                if let None = self.unsafe_fn.iter().position(|info| (*info).id == id){
                    self.unsafe_fn.push(ItemCompilerInfo::new(id, span));
                }
            }
            MyUnsafeFn => {
                if safety {
                    self.safe_fn.push(ItemCompilerInfo::new(id, span));
                }
                else{
                    self.unsafe_fn.push(ItemCompilerInfo::new(id, span));
                }
            }
        }
        
    }
}

impl<'tcx> Visitor<'tcx> for ItemVisitor<'tcx> {
    type Map = Map<'tcx>;
    type NestedFilter = rustc_middle::hir::nested_filter::All;
    fn nested_visit_map<'this>(&'this mut self) -> Self::Map {
        self.tcx.hir()
    }

    fn visit_block(&mut self, b: &'tcx rustc_hir::Block) {
        match b.rules {
            rustc_hir::BlockCheckMode::DefaultBlock => { self.safe_block_num += 1}
            rustc_hir::BlockCheckMode::UnsafeBlock(_) => {
                // get the unsafe block's owner name, and add to the unsafe block vectors
                self.add(MyUnsafeBlock, b.hir_id.owner.to_def_id(), b.span, false);
                self.unsafe_block_num += 1;
            }
        }
        rustc_hir::intravisit::walk_block(self, b);
    }

    fn visit_item(&mut self, item: &'tcx rustc_hir::Item) {
        // add unsafe trait implement to its vector
        if let rustc_hir::ItemKind::Impl(trait_impl) = &item.kind {
            if let rustc_hir::Unsafety::Unsafe = trait_impl.unsafety{
                self.add(MyUnsafeTraitImpl, item.def_id.to_def_id(), item.span, false);
            }
        } else {
            // add unsafe trait to its vector
            if let rustc_hir::ItemKind::Trait(_, rustc_hir::Unsafety::Unsafe, ..) = item.kind {
                self.add(MyUnsafeTrait, item.def_id.to_def_id(), item.span, false);
            }
        }
        rustc_hir::intravisit::walk_item(self, item);
    }
    fn visit_fn(&mut self, fk: FnKind<'tcx>, fd: &'tcx FnDecl<'tcx>, b: BodyId, s: Span, id: HirId){
        let mut safety: bool = true;
        if let FnKind::ItemFn(_, _, fn_header, ..) = fk{
            if let rustc_hir::Unsafety::Unsafe = fn_header.unsafety{
                safety = false;
            }
        }
        else{
            if let FnKind::Method(_, ref fn_sig, ..) = fk{
                if let rustc_hir::Unsafety::Unsafe = fn_sig.header.unsafety{
                    safety = false;
                }
            }
        }
        self.add(MyUnsafeFn, self.tcx.hir().local_def_id(id).to_def_id(), s, safety);
        rustc_hir::intravisit::walk_fn(self, fk, fd, b, id);
    }
}
