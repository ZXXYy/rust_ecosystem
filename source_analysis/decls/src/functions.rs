use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct FnInfo {
    name: String,
    node_id: String,
    header_span: String,
    body_span: String, 
    unsafety: bool,
}

impl FnInfo {
    pub fn new(name: String, node_id: String, header_span: String, body_span: String, unsafety: bool) -> Self {
        FnInfo {
            name,
            node_id,
            header_span,
            body_span,
            unsafety,
        }
    }
}