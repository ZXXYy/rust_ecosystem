use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct UnsafeItemInfo {
    pub name: String,
    pub safe: bool,
    pub loc: String,
}

impl UnsafeItemInfo {
    pub fn new(name: String, safe: bool, loc: String) -> Self {
        UnsafeItemInfo { name, safe, loc }
    }
}
