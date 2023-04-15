use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct BlockSummary {
    pub user_unsafe_blocks: usize,
    pub unsafe_blocks: usize,
    pub total: usize,
    pub unsafe_blocks_names: Vec<String>
}

impl BlockSummary {
    pub fn new( user_unsafe_blocks: usize, unsafe_blocks: usize, total: usize, unsafe_blocks_names: Vec<String>) -> Self {
        BlockSummary {
            user_unsafe_blocks,
            unsafe_blocks,
            total,
            unsafe_blocks_names
        }
    }
}

#[derive(Serialize, Deserialize, Debug)]
pub struct BlockUnsafety {
    pub fn_id: String,
    pub block_span: String,
    pub unsafety: bool,
}

impl BlockUnsafety {
    pub fn new(fn_id: String, block_span: String, unsafety: bool) -> Self {
        BlockUnsafety {
            fn_id,
            block_span,
            unsafety
        }
    }
}
