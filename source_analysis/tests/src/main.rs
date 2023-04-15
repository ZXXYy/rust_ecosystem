#![feature(plugin)]
#![plugin(unsafeAnalysis)]
use std::fmt::Write;

trait Animal {
    fn name(&self) -> &'static str;
    fn sound(&self) -> &'static str {
        ""
    }
    fn says(&self) -> String {
        let mut buffer = String::new();
        write!(buffer, "The {:?} says {:?}", self.name(), self.sound());
        buffer
    }
}
unsafe trait UnsafeTrait {
   fn safe_method_unsafe_trait(&self) -> ();
   unsafe fn unsafe_method_unsafe_trait(&self) -> ();
   fn m1() -> () {
       let mut i = 1;
       i += 1;
   }
   unsafe fn m2() -> () {
       let mut i = 1;
       i += 1;
   }
}
struct Mouse{}
impl Animal for Mouse {
    fn name(&self) -> &'static str {
        "mouse"
    }
    fn sound(&self) -> &'static str {
        unsafe {"squeak"}
    }
}

struct Fox{}
impl Animal for Fox {
    fn name(&self) -> &'static str {
        "fox"
    }
    fn says(&self) -> String {
        "What does the fox say?".to_string()
    }
}

fn mini_zoo() {
    let mouse = Mouse{};
    let fox = Fox{};
    let mouse_says = mouse.says();
    let fox_says = fox.says();
}

macro_rules! say_hello {
    // `()` indicates that the macro takes no argument.
    () => {
        // The macro will expand into the contents of this block.
        println!("Hello!");
    };
}

fn main() {
    mini_zoo();
    say_hello!();
    // non_exist_fn();
}
