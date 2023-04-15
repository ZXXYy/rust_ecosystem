use serde::{Serialize, Deserialize};
use std::fmt;

use crate::Abi;

#[derive(Serialize, Deserialize, Debug)]
pub struct Source {
    pub loc: String,
    pub kind: SourceKind,
    pub user_provided: bool,
}

#[derive(Serialize, Deserialize)]
pub enum SourceKind {
    UnsafeFnCall(Abi),
    DerefRawPointer,
    Asm,
    Static,
    BorrowPacked,
    AssignmentToNonCopyUnionField,
    AccessToUnionField,
    ExternStatic,
    ConstantFn,
}

impl fmt::Debug for SourceKind {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            SourceKind::BorrowPacked => {write!(f, "Borrow Packed")}
            SourceKind::AssignmentToNonCopyUnionField => {write!(f, "Assign to Union")}
            SourceKind::AccessToUnionField => {write!(f, "Access to Union")}
            SourceKind::ExternStatic => {write!(f, "Extern Static Variable")}
            SourceKind::UnsafeFnCall(_) => {write!(f, "Unsafe Function Call")}
            SourceKind::DerefRawPointer => {write!(f, "Derefence Raw Pointer")}
            SourceKind::Asm => {write!(f, "Assembly")}
            SourceKind::Static => {write!(f, "Global Variable")}
            SourceKind::ConstantFn => {write!(f, "Constant Function")}
        }

    }
}